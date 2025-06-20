# Changelog
- 4.1.38 (2025.06.19)
    - macro.info에 word-wrap:break-word style 추가.
    - 플러그인 setting 에 recent_menu_plugin_except_list 설정 추가.
        - 최근 메뉴 정보 저장시 제외할 목록.
        - UI로 접근할 수 있는 메뉴는 아니지만 필요에 의해 만든 페이지까지 저장되어 재진입시 정상적인 화면으로 못가는 경우가 발생할 때 사용.
    - changelog 출력 관련 showdown CSS 수정.
      ```
      p {
        margin: 6px;
        padding: 0px;
      }

      ul {
        padding-left: 0px;
        margin-left: 25px;
        list-style-position: inside;
      }
      ```
<br><br>
- 4.1.37 (2024.10.09)
    - KLive+ 추가
<br><br>
- 4.1.36 (2024.09.15)   
    - python-socketio 최신 버전 사용하도록 수정.
<br><br>
- 4.1.34 (2024.09.04)
    - socketio connect시 login_required 추가.
<br><br>
- 4.1.33 (2024.09.01)
    - termux 32bit & python 3.11 용 libsc.so 파일 추가.
<br><br>
- 4.1.32 (2024.08.30)
    - termux & python 3.11 용 libsc.so 파일 추가.
<br><br>
- 4.1.31 (2024.08.21)
    - yaml copy_section 버그 수정
<br><br>
- 4.1.30 (2024.08.15)
    - support 패키지 로거 설정 수정
<br><br>
- 4.1.27 (2024.08.10)
    - WEB_DIRECT_URL 삭제.
<br><br>  
- 4.1.26 (2024.07.31)
    - FF 로딩 완료 체크 config 추가.
      F.config['loading_completed']
<br><br>
- 4.1.25 (2024.07.31)
    - FrameWork에 redis db 기본 생성.
      플러그인에서 F.rd 로 접근.
      ```
        # 플러그인 개별 DB 생성하여 활용 코드
        # 생성
        self.rd = redis.StrictRedis(host='localhost', port=F.config['redis_port'], db=self.db_item.id)

        # DB 초기화
        self.rd.flushdb()

        # set
        self.rd.set(key, json.dumps(data))

        # get
        self.rd.get(key)
      ```
<br><br>
- 4.1.24 (2024.07.29)
    - videojs_drm 페이지 추가.
<br><br>
- 4.1.23 (2024.06.30)
    - videojs CDN 변경. 코드 정리.
<br><br>
- 4.1.22 (2024.06.22)
    - EPG 플러그인 추가.  
<br><br>  
- 4.1.20 (2024.06.22)
    - 플러그인 폴더가 . 이나 _ 으로 시작할 경우 로딩하지 않음.
<br><br>
- 4.1.18 (2024.06.19)
    - 시스템 - 플러그인 관리 - 전체 플러그인 목록 추가.
<br><br>
- 4.1.15 (2024.06.19)
    - main.py 에서 CELERYD_HIJACK_ROOT_LOGGER=false export(set)
    - 로그 UI 변경.
    - framework, plugin 전체 로그를 all.log 에 기록.
    - ModelBase에 get_list_by_status 메소드 추가.
<br><br>
- 4.1.14 (2024.06.12)
    = `import flaskfarm` 만으로 전체기능 로딩되지 않게 수정.
<br><br>
- 4.1.11 (2024.06.11)
    - DB 전체(기간) 삭제시 VACUUM 수행.
<br><br>
- 4.1.7 (2024.06.05)
    - 확장 설정에서 하위 페이지(setting_menu 에서 list)를 처리할 수 있도록 수정.
<br><br>
- 4.1.6 (2024.06.04)
    - 확장 설정도 menu.yaml 적용 가능 하도록 수정.
    - 확장 설정에서는 uri가 반드시 플러그인을 나타내지 않기 떄문에 순서를 위해서는 plugin을 key로 사용해야 함.
    예:
    
    ```
    - name: "시스템"
    list:
      - uri: "system"
        name: "설정"
      - uri: "setting"
        name: "확장 설정"
        list:
          - uri: "https://drive.google.com"
            name: 구글 드라이브
          - uri: "-"
          - plugin: "flaskcode"
          - plugin: "terminal"
          - plugin: "flaskfilemanager"
          - uri: "-"
          - plugin: "trans"
          - uri: "-"
          - plugin: "support_site"
          - uri: "-"
    ```
<br><br>
- 4.1.4 (2024.06.01)
    - SuppportString.remove_emoji 추가
