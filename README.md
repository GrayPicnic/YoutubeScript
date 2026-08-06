# YouTube Script Extractor

유튜브 영상 URL을 넣으면 자막(수동/자동 생성)을 가져와 텍스트 또는 SRT 자막 파일로 뽑아주는 로컬 웹 도구입니다.

## 구조

```
main.py             FastAPI 백엔드 (자막 추출 + 포맷 변환)
static/index.html   프론트엔드 전체 (UI + CSS + JS, 단일 파일)
requirements.txt    의존성
run.bat             Windows 실행 스크립트
```

프론트엔드는 빌드 과정이 없는 순수 HTML/CSS/JS 단일 파일입니다. Node/npm 불필요.

## 실행 방법

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

실행하면 브라우저가 자동으로 `http://127.0.0.1:8787` 로 열립니다.
Windows에서는 `run.bat` 더블클릭으로도 실행 가능합니다.

## 기능

- 유튜브 URL 입력 → 자막 추출 (수동/자동 생성 자막 모두 지원)
- 출력 형식 3종: SRT 자막 파일(기본) / 일반 텍스트 / 타임스탬프 포함 텍스트
- URL 입력 시 썸네일 자동 미리보기
- 입력칸 X 버튼으로 전체 초기화, URL 수정 시 결과 자동 초기화
- 결과 영역 줄 번호 표시 (스크롤 동기화)
- 라이트/다크 테마 전환 (선택값 localStorage 저장, 기본 라이트)
- 결과 복사 및 파일 다운로드 (`.srt` / `.txt`)
- 반응형 레이아웃 (모바일 ~ 와이드 모니터)

## API

`POST /api/extract`

```json
{ "url": "https://youtube.com/watch?v=...", "format": "srt" }
```

`format`: `srt` (기본) | `plain` | `timestamped`

## 단일 exe로 빌드

```bash
pip install pyinstaller
pyinstaller --onefile --name youtube-script-extractor --add-data "static;static" --collect-all yt_dlp --collect-all uvicorn --collect-all fastapi main.py
```

결과물은 `dist/youtube-script-extractor.exe` (약 27MB). Python 설치 없이 단독 실행됩니다.

### 배포

exe는 저장소가 아니라 **GitHub Releases**로 배포합니다. 랜딩 페이지의 다운로드 버튼은
`releases/latest/download/youtube-script-extractor.exe` 를 가리키므로, 새 릴리스를 올리기만 하면
링크는 그대로 두어도 최신 파일을 가리킵니다. **파일명은 반드시 유지하세요.**

원래는 `docs/` 에 exe를 넣어 Pages가 직접 서빙했는데, 27MB 파일이 아티팩트에 들어가면서
`Deploy to GitHub Pages` 단계가 10분 타임아웃으로 두 번 연속 실패했습니다 (빌드 job 자체는 12초 만에 성공).
exe를 빼자 아티팩트가 27MB → 1.1MB 로 줄었습니다. 다시 넣지 마세요.

## 제약

- 자막이 없는 영상은 지원하지 않습니다. (음성 인식 기능은 로컬 CPU 환경에서 속도·정확도가 떨어져 제거했습니다.)
- 개인용 로컬 도구입니다. 외부 서비스로 배포하려면 호스팅·동시성·유튜브 rate limit을 별도로 고려해야 합니다.

## 개발 노트 (이미 시도해보고 막힌 것들)

다시 시도하기 전에 읽어보세요. 아래는 모두 실제로 해보고 확인된 내용입니다.

**1. 서버 없는 단일 HTML로는 못 만듭니다.**
브라우저에서 유튜브 페이지를 fetch해 자막 트랙 URL을 얻는 것까지는 되지만, 마지막 `timedtext` API 요청이 빈 응답(200 + 길이 0)을 반환합니다. 유튜브가 브라우저 직접 요청을 차단합니다. 서버(Python)에서 요청할 때만 정상 동작하므로 백엔드가 반드시 필요합니다.

**2. 로컬 Whisper 음성 인식은 실용성이 없었습니다.**
`faster-whisper` small 모델 + CPU int8로 구현했으나, 고유명사 오인식이 심했습니다 (Far Cry → "fuckrun", cross-studio → "crusted your", Battlefield → "belfry/belgium"). 정확도를 올리려면 medium/large 모델이 필요하지만 CPU에서 처리 시간이 3~5배 이상 늘어납니다. 그래서 제거했습니다. 다시 넣으려면 GPU 또는 외부 API를 쓰세요.

**3. m3u8 전용 영상은 ffmpeg가 필요했습니다.**
Whisper 기능을 되살릴 경우, 일부 영상은 HLS 스트림만 제공해서 `ffmpeg` 없이는 오디오 다운로드가 실패합니다 (`winget install Gyan.FFmpeg`).

**4. 결과 박스가 페이지를 늘리는 버그. (구조 변경됨)**
원래는 `.result-body`에 고정 높이(420px)를 주고 자녀를 `height:100%`로 잡는 방식이었습니다. 그런데 URL을 입력해 썸네일이 나타나는 순간 카드가 238px 늘어나면서 결과 박스가 화면 아래로 468px 밀려나는 문제가 있었습니다.

지금은 뷰포트 고정 방식입니다:
- `.container`에 `max-height:calc(100vh - 80px)` + `display:flex; flex-direction:column`
- 고정 영역(header/controls/thumbnail/progress/status/footer)은 전부 `flex:0 0 auto`
- `.result`와 `.result-body`가 `flex:1 1 auto; min-height:0`으로 남는 높이를 흡수 (바닥값 200px)

즉 썸네일이 뜨면 페이지가 길어지는 대신 결과 박스가 줄어듭니다.

**중요:** 이 구조에서 자녀의 `height:100%`는 **작동하지 않습니다.** 부모 높이가 flex 계산으로 정해져서 퍼센트 높이가 해석되지 않고, 자녀가 콘텐츠 높이로 쪼그라듭니다 (실제로 textarea가 200px 대신 98px이 됐습니다). `.line-numbers`와 `textarea`에서 `height:100%`를 빼고 `min-height:0`만 두어, flex 기본값인 `align-items:stretch`가 늘리도록 해야 합니다.

모바일(`max-width:640px`)은 예외로 `max-height:none` + `.result-body{ flex:0 0 auto; height:320px }`를 써서 페이지 스크롤을 허용합니다. 좁은 화면에서 뷰포트 고정은 너무 답답해집니다.

**5. 포트 8787이 이미 사용 중이면 조용히 죽습니다.**
이전 인스턴스가 살아있는 상태에서 실행하면 `[Errno 10048]` 바인딩 실패로 종료됩니다. `run.bat`은 오류를 볼 수 있게 `pause`를 넣어뒀습니다. 확인: `netstat -ano | findstr :8787`

**6. 테마 깜빡임 방지.**
테마는 `<head>`의 인라인 스크립트에서 첫 렌더링 전에 적용합니다. 이 로직을 body 하단으로 옮기면 로드 시 색이 깜빡입니다.
