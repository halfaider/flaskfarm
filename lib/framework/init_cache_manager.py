import redis

class _RedisManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, host='localhost', port=6379):
        if hasattr(self, 'redis_client'):
            return
        
        try:
            self.redis_client = redis.Redis(host=host, port=port, db=1, decode_responses=True)
            self.redis_client.ping()
            self.is_redis = True
        except redis.exceptions.ConnectionError:
            self.is_redis = False
            self.cache_backend = {} # Redis 실패 시 메모리 캐시 사용
    
    def set(self, key, value, ex=None):
        if self.is_redis:
            self.redis_client.set(key, value, ex=ex)
        else:
            self.cache_backend[key] = value

    def get(self, key):
        if self.is_redis:
            return self.redis_client.get(key)
        else:
            return self.cache_backend.get(key)
            
    def delete(self, key):
        if self.is_redis:
            self.redis_client.delete(key)
        else:
            if key in self.cache_backend:
                del self.cache_backend[key]


#_redis_manager_instance = _RedisManager()

class NamespacedCache:
    def __init__(self, namespace):
        self._manager = _RedisManager._instance
        self.namespace = namespace

    def _make_key(self, key):
        # 'plugin_name:key' 형식으로 실제 키를 생성
        return f"{self.namespace}:{key}"

    def set(self, key, value, ex=None):
        full_key = self._make_key(key)
        self._manager.set(full_key, value, ex=ex)

    def get(self, key):
        full_key = self._make_key(key)
        return self._manager.get(full_key)

    def delete(self, key):
        full_key = self._make_key(key)
        self._manager.delete(full_key)


def get_cache(plugin_name: str) -> NamespacedCache:
    """
    플러그인 이름을 기반으로 네임스페이스가 적용된 캐시 객체를 반환합니다.
    """
    if not plugin_name:
        raise ValueError("플러그인 이름은 필수입니다.")
    return NamespacedCache(plugin_name)