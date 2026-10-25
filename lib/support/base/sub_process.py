import codecs
import json
import os
import platform
import queue
import select
import signal
import subprocess
import threading
import time
import traceback

from . import logger


_STREAM_END = object()
_CALLBACK_END = object()
_CALLBACK_START = object()


def _close_pipe(pipe, command=None):
    if pipe is not None and not pipe.closed:
        try:
            pipe.close()
        except (OSError, ValueError) as e:
            logger.warning(
                'Failed to close subprocess pipe for command %r: %s', command, e
            )


def _read_process_stdout(process, on_chunk):
    decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
    stream = process.stdout
    if stream is None:
        return

    skip_lf = False

    def emit_text(text):
        nonlocal skip_lf
        if skip_lf and text:
            if text.startswith('\n'):
                text = text[1:]
            skip_lf = False
        if text:
            skip_lf = text.endswith('\r')
            on_chunk(text.replace('\r\n', '\n').replace('\r', '\n'))

    fd = os.dup(stream.fileno())
    try:
        poller = None
        if platform.system() != 'Windows':
            poller = select.poll()
            poller.register(fd, select.POLLIN | select.POLLHUP | select.POLLERR)
        else:
            import ctypes
            import msvcrt
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            peek_named_pipe = kernel32.PeekNamedPipe
            peek_named_pipe.argtypes = (
                wintypes.HANDLE,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.LPVOID,
                ctypes.POINTER(wintypes.DWORD),
                wintypes.LPVOID,
            )
            peek_named_pipe.restype = wintypes.BOOL
            available = wintypes.DWORD()
            handle = msvcrt.get_osfhandle(fd)

        drain_deadline = None
        while True:
            if process.poll() is not None:
                if drain_deadline is None:
                    drain_deadline = time.monotonic() + 2
                elif time.monotonic() >= drain_deadline:
                    break

            if poller is not None:
                if not poller.poll(100):
                    continue
                read_size = 4096
            else:
                if not peek_named_pipe(
                    wintypes.HANDLE(handle), None, 0, None, ctypes.byref(available), None
                ):
                    error_code = ctypes.get_last_error()
                    if error_code == 109:
                        break
                    raise ctypes.WinError(error_code)
                if available.value == 0:
                    time.sleep(0.05)
                    continue
                read_size = min(4096, available.value)

            chunk = os.read(fd, read_size)
            if not chunk:
                break
            emit_text(decoder.decode(chunk))

        emit_text(decoder.decode(b'', final=True))
    finally:
        os.close(fd)


def demote(user_uid, user_gid):
    def result():
        if user_gid is not None:
            os.setgid(user_gid)
        os.setuid(user_uid)
    return result

class SupportSubprocess(object):
    """Run a subprocess and forward its output through a serialized callback.

    The callback must return in finite time. A callback that blocks indefinitely
    also blocks delivery of terminal events; Python threads cannot be safely
    force-stopped.
    """

    @classmethod
    def command_for_windows(cls, command: list): 
        if platform.system() == 'Windows':
            tmp = []
            if type(command) == type([]):
                for x in command:
                    if x.find(' ') == -1:
                        tmp.append(x)
                    else:
                        tmp.append(f'"{x}"')
                command = ' '.join(tmp)
        return command

    # 2021-10-25
    # timeout 적용
    @classmethod
    def execute_command_return(cls, command, format=None, log=False, shell=False, env=None, timeout=None, uid=None, gid=None):
        process = None
        try:
            logger.debug('execute_command_return : %r', command)
            command = cls.command_for_windows(command)

            popen_options = {
                'stdin': subprocess.PIPE,
                'stdout': subprocess.PIPE,
                'stderr': subprocess.STDOUT,
                'universal_newlines': True,
                'shell': shell,
                'env': env,
                'encoding': 'utf8',
                'errors': 'replace',
            }
            if platform.system() == 'Windows':
                popen_options['bufsize'] = 0
            elif uid is not None:
                popen_options['preexec_fn'] = demote(uid, gid)
            if platform.system() != 'Windows':
                popen_options['start_new_session'] = True
            process = subprocess.Popen(command, **popen_options)
            new_ret = {'status':'finish', 'log':None}

            if log:
                output_chunks = []
                pending_log = ['']

                def capture_and_log(chunk):
                    output_chunks.append(chunk)
                    pending_log[0] += chunk
                    lines = pending_log[0].split('\n')
                    pending_log[0] = lines.pop()
                    for line in lines:
                        logger.debug('%s', line)

                _close_pipe(process.stdin, command)

                reader_errors = []

                def read_and_capture():
                    try:
                        _read_process_stdout(process, capture_and_log)
                    except Exception as e:
                        reader_errors.append(e)
                        try:
                            cls.__kill_process_tree(process)
                        except Exception:
                            logger.exception(
                                'Failed stopping subprocess after stdout read error for command %r',
                                command,
                            )

                reader = threading.Thread(
                    target=read_and_capture,
                    daemon=True,
                )
                reader.start()
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    new_ret['status'] = 'timeout'
                    logger.warning(
                        'Command %r timed out after %s seconds', command, timeout
                    )
                    cls.__kill_process_tree(process)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                reader.join(timeout=3)
                if reader.is_alive():
                    logger.warning(
                        'Subprocess output reader did not stop before deadline for command %r',
                        command,
                    )
                    _close_pipe(process.stdout, command)
                    reader.join(timeout=1)
                if reader.is_alive():
                    raise RuntimeError(
                        'Subprocess output reader did not stop; output may be incomplete'
                    )
                if reader_errors:
                    raise reader_errors[0]
                if pending_log[0]:
                    logger.debug('%s', pending_log[0])
                output = ''.join(output_chunks)
            else:
                try:
                    output, _ = process.communicate(timeout=timeout)
                except subprocess.TimeoutExpired:
                    new_ret['status'] = 'timeout'
                    logger.warning(
                        'Command %r timed out after %s seconds', command, timeout
                    )
                    cls.__kill_process_tree(process)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    try:
                        output, _ = process.communicate(timeout=5)
                    except subprocess.TimeoutExpired as e:
                        output = e.output or ''

            if isinstance(output, bytes):
                output = output.decode('utf-8', errors='replace')

            lines = output.split('\n')
            if lines and lines[-1] == '':
                lines.pop()
            ret = [line.strip() for line in lines]
            if format is None:
                ret2 = '\n'.join(ret)
            elif format == 'json':
                try:
                    index = 0
                    for idx, tmp in enumerate(ret):
                        #logger.debug(tmp)
                        if tmp.startswith('{') or tmp.startswith('['):
                            index = idx
                            break
                    ret2 = json.loads(''.join(ret[index:]))
                except:
                    ret2 = ret
            else:
                ret2 = ret

            new_ret['log'] = ret2
            return new_ret
        except Exception:
            logger.exception(
                'Failed executing subprocess command %r (timeout=%r)', command, timeout
            )
        finally:
            if process is not None:
                if process.poll() is None:
                    cls.__kill_process_tree(process)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                for pipe in (process.stdin, process.stdout):
                    _close_pipe(pipe, getattr(process, 'args', None))

    

    __instance_list = []
    __instance_lock = threading.RLock()


    def __init__(self, command,  print_log=False, shell=False, env=None, timeout=None, uid=None, gid=None, stdout_callback=None, call_id=None, callback_line=True):
        self.command = command
        self.print_log = print_log
        self.shell = shell
        self.env = env
        self.timeout = timeout
        self.uid = uid
        self.gid = gid
        self.stdout_callback = stdout_callback
        self.process = None
        self.stdout_queue = None
        self.call_id = call_id
        self.timestamp = time.time()
        self.callback_line = callback_line
        self.reader_thread = None
        self.collector_thread = None
        self.callback_thread = None
        self.output_queue = None
        self.__output_error = None
        self.__process_lock = threading.Lock()
        self.__stop_requested = False
        self.__last_callback = time.monotonic()
        self.__callback_terminal_error = None
        self.__callback_terminal_lock = threading.Lock()
        self.__callback_terminal_sent = threading.Event()

    def start(self, join=True):
        try:
            with self.__instance_lock:
                self.__instance_list.append(self)
            self.thread = threading.Thread(
                target=self.__execute_thread_function, daemon=True
            )
            self.thread.start()
            if join:
                self.thread.join()
        except Exception:
            logger.exception('Failed to start subprocess command %r', self.command)
            self.remove_instance(self)
            self.send_stdout_callback(self.call_id, 'ERROR', traceback.format_exc())
            self.send_stdout_callback(self.call_id, 'END', None)


    def __execute_thread_function(self):
        process = None
        error = None
        try:
            self.command = self.command_for_windows(self.command)
            logger.debug('Starting subprocess command %r', self.command)
            popen_options = {
                'stdin': subprocess.PIPE,
                'stdout': subprocess.PIPE,
                'stderr': subprocess.STDOUT,
                'universal_newlines': True,
                'shell': self.shell,
                'env': self.env,
                'encoding': 'utf8',
                'errors': 'replace',
                'bufsize': 0,
            }
            if platform.system() != 'Windows' and self.uid is not None:
                popen_options['preexec_fn'] = demote(self.uid, self.gid)
            if platform.system() != 'Windows':
                popen_options['start_new_session'] = True
            process = subprocess.Popen(self.command, **popen_options)
            with self.__process_lock:
                self.process = process
                stop_requested = self.__stop_requested
            if stop_requested:
                self.process_close()
            self.__start_communicate()
            process.wait(timeout=self.timeout)
            logger.info('Subprocess command %r END', self.command)
        except subprocess.TimeoutExpired:
            error = 'Command timed out after %s seconds' % self.timeout
            logger.warning(
                'Subprocess command %r timed out after %s seconds',
                self.command,
                self.timeout,
            )
            if process is not None:
                self.__kill_process_tree(process)
        except Exception:
            error = traceback.format_exc()
            logger.exception('Failed running subprocess command %r', self.command)
        finally:
            if process is not None:
                try:
                    if process.poll() is None:
                        self.process_close()
                    process.wait()
                except Exception:
                    error = error or traceback.format_exc()
                    logger.exception('Failed waiting for subprocess command %r', self.command)
                for thread in (self.reader_thread, self.collector_thread):
                    if thread is not None:
                        try:
                            thread.join(timeout=3)
                            if thread.is_alive():
                                error = error or 'Subprocess output reader did not stop before its deadline'
                                logger.warning(
                                    '%s (command=%r)', error, self.command
                                )
                                if self.output_queue is not None:
                                    self.output_queue.put(None)
                                if self.stdout_queue is not None:
                                    self.stdout_queue.put(_STREAM_END)
                                thread.join(timeout=1)
                        except Exception:
                            error = error or traceback.format_exc()
                            logger.exception(
                                'Failed joining output worker for command %r', self.command
                            )
                self.__close_pipes(process)

            error = error or self.__output_error
            callback_started = (
                self.callback_thread is not None
                and self.callback_thread.ident is not None
            )
            if callback_started:
                with self.__callback_terminal_lock:
                    self.__callback_terminal_error = (
                        self.__callback_terminal_error or error
                    )
                self.stdout_queue.put(_STREAM_END)
                self.stdout_queue.put(_CALLBACK_END)
                try:
                    self.__last_callback = time.monotonic()
                    while self.callback_thread.is_alive():
                        self.callback_thread.join(timeout=1)
                        if (
                            self.callback_thread.is_alive()
                            and time.monotonic() - self.__last_callback > 10
                        ):
                            error = error or 'Subprocess callback is not responding'
                            with self.__callback_terminal_lock:
                                self.__callback_terminal_error = error
                            logger.warning('%s (command=%r)', error, self.command)
                            break
                except Exception:
                    error = error or traceback.format_exc()
                    with self.__callback_terminal_lock:
                        self.__callback_terminal_error = error
                    logger.exception(
                        'Failed joining callback worker for command %r', self.command
                    )
                if (
                    not self.callback_thread.is_alive()
                    and not self.__callback_terminal_sent.is_set()
                ):
                    with self.__callback_terminal_lock:
                        terminal_error = self.__callback_terminal_error
                    if terminal_error is not None:
                        self.send_stdout_callback(
                            self.call_id, 'ERROR', terminal_error
                        )
                    self.send_stdout_callback(self.call_id, 'END', None)
                    self.__callback_terminal_sent.set()
            else:
                if error is not None:
                    self.send_stdout_callback(self.call_id, 'ERROR', error)
                if process is not None or error is not None:
                    self.send_stdout_callback(self.call_id, 'END', None)
            self.remove_instance(self)
            with self.__process_lock:
                self.process = None

    @staticmethod
    def __close_pipes(process):
        if process is not None:
            for stream in (process.stdin, process.stdout, process.stderr):
                _close_pipe(stream, getattr(process, 'args', None))

    def __start_communicate(self):
        self.stdout_queue = queue.Queue()
        stdout_queue = self.stdout_queue
        stdout_queue.put(_CALLBACK_START)
        process = self.process
        output_queue = self.output_queue = queue.Queue()
        if process is None or process.stdout is None:
            raise RuntimeError('Subprocess stdout is unavailable')

        def read_stdout():
            try:
                _read_process_stdout(process, output_queue.put)
            except Exception:
                self.__output_error = traceback.format_exc()
                logger.exception('Failed reading subprocess output for command %r', self.command)
                self.process_close()
            finally:
                output_queue.put(None)

        def collect_output():
            try:
                while True:
                    chunk = output_queue.get()
                    if chunk is None:
                        break
                    finished = False
                    chunk_size = len(chunk)
                    while chunk_size < 65536:
                        try:
                            following = output_queue.get(timeout=0.005)
                        except queue.Empty:
                            break
                        if following is None:
                            finished = True
                            break
                        chunk += following
                        chunk_size += len(following)
                    stdout_queue.put(chunk)
                    if finished:
                        break
            except Exception:
                self.__output_error = self.__output_error or traceback.format_exc()
                logger.exception(
                    'Failed collecting subprocess output for command %r', self.command
                )
            finally:
                stdout_queue.put(_STREAM_END)

        self.reader_thread = threading.Thread(target=read_stdout, daemon=True)
        self.collector_thread = threading.Thread(target=collect_output, daemon=True)
        self.__start_send_callback()
        self.reader_thread.start()
        self.collector_thread.start()


    def __start_send_callback(self):
        def send_callback():
            previous = ''
            try:
                while True:
                    item = self.stdout_queue.get()
                    if item is _CALLBACK_START:
                        self.send_stdout_callback(self.call_id, 'START', None)
                        continue
                    if item is _STREAM_END:
                        break

                    chunks = [item]
                    chunk_size = len(item)
                    while chunk_size < 65536:
                        try:
                            item = self.stdout_queue.get(timeout=0.005)
                        except queue.Empty:
                            break
                        if item is _STREAM_END:
                            break
                        chunks.append(item)
                        chunk_size += len(item)

                    receive = ''.join(chunks)
                    if self.callback_line:
                        lines = (previous + receive).split('\n')
                        previous = lines.pop()
                        for line in lines:
                            self.send_stdout_callback(self.call_id, 'LOG', line.strip())
                    else:
                        self.send_stdout_callback(self.call_id, 'LOG', receive)

                    if item is _STREAM_END:
                        break

                if self.callback_line and previous:
                    self.send_stdout_callback(self.call_id, 'LOG', previous.strip())
            except Exception:
                with self.__callback_terminal_lock:
                    self.__callback_terminal_error = (
                        self.__callback_terminal_error or traceback.format_exc()
                    )
                logger.exception(
                    'Failed forwarding subprocess output for command %r', self.command
                )
            finally:
                while self.stdout_queue.get() is not _CALLBACK_END:
                    pass
                with self.__callback_terminal_lock:
                    error = self.__callback_terminal_error
                try:
                    if error is not None:
                        self.send_stdout_callback(self.call_id, 'ERROR', error)
                    self.send_stdout_callback(self.call_id, 'END', None)
                finally:
                    self.__callback_terminal_sent.set()

        self.callback_thread = threading.Thread(target=send_callback, daemon=True)
        self.callback_thread.start()



    def process_close(self):
        with self.__process_lock:
            self.__stop_requested = True
            process = self.process
        try:
            if process is not None:
                self.__kill_process_tree(process)
        except Exception:
            logger.exception('Failed to stop subprocess command %r', self.command)

    @staticmethod
    def __kill_process_tree(process):
        if process.poll() is not None:
            return

        if platform.system() != 'Windows':
            # Policy: stop the group only while its leader is alive. This avoids
            # signaling a reused PID; descendants left after normal leader exit
            # are outside this cleanup path's supervision.
            if process.poll() is not None:
                return
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as e:
                logger.warning(
                    'Could not terminate subprocess group for command %r: %s',
                    getattr(process, 'args', None),
                    e,
                )
            if process.poll() is None:
                process.kill()
            return

        try:
            import psutil
        except ImportError:
            psutil = None

        if psutil is not None:
            try:
                children = psutil.Process(process.pid).children(recursive=True)
                for child in children:
                    try:
                        child.kill()
                    except psutil.Error:
                        pass
            except psutil.Error as e:
                logger.debug(
                    'Could not inspect subprocess children for command %r: %s',
                    getattr(process, 'args', None),
                    e,
                )

        if process.poll() is None:
            process.kill()

    def input_command(self, cmd):
        with self.__process_lock:
            process = self.process
        if process is not None and process.stdin is not None and not process.stdin.closed:
            process.stdin.write(f'{cmd}\n')
            process.stdin.flush()

    def send_stdout_callback(self, call_id, mode, data):
        self.__last_callback = time.monotonic()
        try:
            if self.stdout_callback != None:
                self.stdout_callback(self.call_id, mode, data)
        except Exception:
            logger.exception(
                'Subprocess callback failed for command %r (call_id=%r, mode=%r, data=%r)',
                self.command,
                call_id,
                mode,
                data,
            )


    @classmethod
    def all_process_close(cls):
        with cls.__instance_lock:
            instances = list(cls.__instance_list)
        for instance in instances:
            instance.process_close()

    @classmethod
    def remove_instance(cls, remove_instance):
        with cls.__instance_lock:
            cls.__instance_list = [
                instance for instance in cls.__instance_list
                if instance is not remove_instance
            ]
    
    @classmethod
    def print(cls):
        with cls.__instance_lock:
            instances = list(cls.__instance_list)
        for instance in instances:
            logger.info('%s', instance.command)

    @classmethod
    def get_instance_by_call_id(cls, call_id):
        with cls.__instance_lock:
            instances = list(cls.__instance_list)
        for instance in instances:
            if instance.call_id == call_id:
                return instance
    
    @classmethod
    def get_list(cls):
        with cls.__instance_lock:
            return list(cls.__instance_list)