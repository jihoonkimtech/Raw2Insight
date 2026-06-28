# 📊 Raw2Insight
Edge AI-based Dynamic Sensor & Actuator Orchestration Platform for Arduino App Lab

![Platform](https://img.shields.io/badge/Platform-Arduino%20UNO%20Q-00979D?style=for-the-badge&logo=arduino) <br>
![Environment](https://img.shields.io/badge/Environment-Arduino%20App%20Lab-blue?style=for-the-badge) <br>
![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python) <br>
![ML](https://img.shields.io/badge/AI-Scikit_Learn-F7931E?style=for-the-badge&logo=scikit-learn) <br>

**Raw2Insight**는 Arduino App Lab 환경에서 동작하는 **실시간 엣지 AI 스마트 관제 시스템**입니다.  
Arduino UNO Q의 하드웨어 I/O와 Linux 기반 Python 오케스트레이션 레이어를 결합해, **센서 데이터 수집 → 시계열 저장 → 이상 감지 → 액추에이터 제어 → Web UI 브로드캐스팅**까지 하나의 파이프라인으로 처리합니다.

웹 대시보드에서 코딩 없이 센서와 액추에이터를 동적으로 등록할 수 있으며, 내장된 이상 감지 로직이 실시간으로 데이터의 이상 징후를 판단해 디지털 출력 또는 PWM 비례 제어를 수행합니다.

---

## ✨ 주요 기능 (Key Features)

### 🧠 1. Edge AI 실시간 이상 감지 (Anomaly Detection)
- **Scikit-learn Isolation Forest** 기반 이상 감지 모델을 엣지 단에서 직접 실행합니다.
- 아날로그/ I2C 센서 데이터의 최근 시계열 패턴을 학습해 **이상 여부(True/False)**, **방향성(HIGH/LOW)**, **이상 점수(Anomaly Score)**를 계산합니다.
- 센서별 민감도(`sensitivity`)를 다르게 설정할 수 있으며, 민감도 변경 시 모델을 재구성합니다.
- 디지털 센서는 머신러닝 대신 **규칙 기반 판정**으로 처리합니다.

### ⚡ 2. 동적 장치 관리 (Dynamic Device Management)
- 하드웨어 펌웨어를 계속 수정하지 않아도, 웹 UI에서 센서와 액추에이터를 즉시 추가/삭제할 수 있습니다.
- 지원 센서 프로토콜:
  - `analog`
  - `digital`
  - `i2c`
- 지원 액추에이터 타입:
  - `digital_out`
  - `pwm`

### 🔌 3. I2C 플러그인 아키텍처 (I2C Plugin Architecture)
- `sensors/` 디렉토리에 파이썬 클래스를 추가하면 새로운 I2C 센서 드라이버를 동적으로 확장할 수 있습니다.
- 각 드라이버는 `BaseI2CSensor`를 상속받아 `read_bytes`, `default_addr`, `outputs`, `parse()`를 구현합니다.
- 런타임에 프로필이 로드되어 웹 UI에서 선택할 수 있습니다.

### ⚙️ 4. 지능형 액추에이터 제어 (Smart Actuator Control)
- 이상 감지 결과에 따라 연동된 액추에이터를 자동으로 제어합니다.
- **PWM 비례 제어**를 통해 이상 강도에 따라 모터 속도나 LED 밝기를 유연하게 조절할 수 있습니다.
- 임계값 기반 수동 판정과 AI 판정을 함께 사용합니다.
- 액추에이터별로 다음 옵션을 지원합니다.
  - `trigger_dir` (`HIGH`, `LOW`, `BOTH`)
  - `delay`
  - `latch`

### 🧩 5. 가상 액추에이터 (Virtual Actuators)
- 물리 액추에이터 외에도 다음과 같은 가상 장치를 지원합니다.
  - `virtual_counter`
  - `virtual_timer`
  - `virtual_latch`
  - `virtual_webhook`
- 누적 감지 횟수 표시, 상태 유지, 웹훅 알림 등 소프트웨어 기반 자동화가 가능합니다.

### 📈 6. 실시간 웹 대시보드 (Real-time Web UI)
- WebUI를 통해 실시간 센서 시계열 데이터와 이상 상태를 시각화합니다.
- 최근 집계 데이터와 원시 데이터(raw)를 함께 표시할 수 있습니다.
- CPU, RAM 사용량 등 시스템 상태도 함께 모니터링합니다.
- 장치 등록/관리 화면과 모니터링 화면이 분리된 SPA 구조입니다.

---

## 🚀 시작하기 (Getting Started)

### 1. 하드웨어 요구사항
- **Arduino UNO Q**
- Arduino App Lab 개발 환경

### 2. 실행 환경
- Python 3.x
- `numpy`
- `scikit-learn`
- `psutil`

프로젝트 의존성은 `requirements.txt`를 통해 관리됩니다.

### 3. App 구성 요소
이 프로젝트는 Arduino App Lab의 브릭 구성을 사용합니다.

#### `app.yaml`
```yaml
bricks:
- arduino:web_ui: {}
- arduino:dbstorage_tsstore: {}
- arduino:dbstorage_sqlstore: {}
description: ''
icon: 📊
name: Raw2Insight
ports: []
```

#### `sketch.yaml`
```yaml
profiles:
  default:
    platforms:
      - platform: arduino:zephyr
    libraries: {}
default_profile: default
```

### 4. 실행 방법
1. Arduino App Lab에 프로젝트를 등록합니다.
2. App Lab에서 `Run` 버튼을 클릭합니다.
3. `sketch.ino`가 MCU 레이어에서 동작합니다.
4. `main.py`가 Python 오케스트레이터로 실행되며 WebUI, DB, AI 루프를 초기화합니다.
5. 제공되는 WebUI 링크로 접속해 센서와 액추에이터를 등록합니다.

---

## 💡 웹 UI 사용 방법 (How to Use)

1. **대시보드 접속**: 처음 접속하면 아직 등록된 장치가 없을 수 있습니다.
2. **장치 관리 탭 이동**: 상단 메뉴에서 장치 설정 화면으로 이동합니다.
3. **센서 추가**: 프로토콜(`Analog`, `Digital`, `I2C`), 핀 또는 주소, 이름, 단위, 임계값 등을 입력해 등록합니다.
4. **I2C 센서 선택**: I2C 사용 시 로드된 센서 프로필과 데이터 키를 선택합니다.
5. **액추에이터 추가**: 디지털 출력 또는 PWM 장치를 등록하고, 연동할 센서를 선택합니다.
6. **트리거 설정**: `trigger_dir`, 출력값, `delay`, `latch`, 웹훅 옵션 등을 구성합니다.
7. **모니터링**: 대시보드에서 실시간 센서 데이터와 이상 상태를 확인합니다. AI 모델은 데이터가 충분히 쌓인 뒤 자동으로 동작합니다.

---

## 🏗️ 시스템 아키텍처 및 엣지 파이프라인 (System Architecture)

Raw2Insight는 **실시간 하드웨어 제어(MCU)**와 **데이터 처리·AI·네트워크(MPU/Python)**를 분리한 하이브리드 구조를 사용합니다.

- **[MCU Layer]** `sketch/sketch.ino`
  - Analog / Digital / I2C 입력 처리
  - Digital / PWM 출력 제어
  - Bridge RPC 제공
- **[MPU / Python Layer]** `python/main.py` 및 매니저 모듈
  - 센서 폴링
  - 시계열 저장
  - 이상 감지
  - 액추에이터 제어
  - WebUI 브로드캐스팅
- **[Storage Layer]**
  - `TimeSeriesStore`: 센서 시계열 데이터 저장
  - `SQLStore`: 센서/액추에이터 설정 저장
- **[Frontend Layer]** `assets/index.html`
  - 실시간 모니터링
  - 장치 설정 UI

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      [ Real-time Web UI Dashboard ]                    │
 └───────────────────────────────────▲────────────────────────────────────┘
                                     │ (WebUI Message Stream)
 ┌───────────────────────────────────▼────────────────────────────────────┐
 │                         [ MPU Layer : Python ]                         │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │             main.py (Centralized Orchestrator Loop)              │  │
 │  └───────┬─────────────────┬───────────────────▲───────────────┬────┘  │
 │          │                 │                   │               │       │
 │  ┌───────▼───────┐  ┌──────▼───────┐   ┌───────┴───────┐  ┌────▼────┐  │
 │  │  SQLStore     │  │ TimeSeries   │   │  AI Manager   │  │ Web Svr │  │
 │  │(Device Config)│  │   Store      │   │(Isolation F.) │  │(WebUI)  │  │
 │  └───────────────┘  └──────────────┘   └───────────────┘  └─────────┘  │
 └───────────────────────────────────▲────────────────────────────────────┘
                                     │ (Arduino Router Bridge RPC)
 ┌───────────────────────────────────▼────────────────────────────────────┐
 │                        [ MCU Layer : STM32 ]                           │
 │        sketch.ino (Low-Level Peripheral I/O + RPC Provider)            │
 │  ┌───────────────────┬───────────────────┬──────────────────────────┐  │
 │  │    Analog Pins    │   Digital Pins    │     I2C Bus Hardware     │  │
 │  └───────────────────┴───────────────────┴──────────────────────────┘  │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 데이터 파이프라인 플로우

1. **Polling & RPC Request**  
   `main.py`가 등록된 센서 목록을 읽고, `comm_manager.py`를 통해 MCU에 센서 값을 요청합니다.

2. **Hardware I/O & Parsing**  
   MCU(`sketch.ino`)는 아날로그/디지털/I2C 데이터를 읽어 Bridge RPC로 반환합니다.  
   I2C의 경우 필요한 바이트 배열을 읽은 뒤, Python 센서 프로필에서 이를 물리값으로 파싱합니다.

3. **Storage**  
   수집된 센서 값은 `db_manager.py`를 통해 `TimeSeriesStore`에 기록됩니다.

4. **Aggregation & Feature Window**  
   최근 10분 데이터에서 집계값과 원시값을 읽어 AI 판단과 UI 표시용으로 사용합니다.

5. **Edge AI Inference**  
   `ai_manager.py`가 최근 시계열에 대해 Isolation Forest를 적용하여 이상 여부와 방향성을 계산합니다.

6. **Threshold + Hysteresis Decision**  
   AI 판정 외에도 사용자 임계값(`threshold_low`, `threshold_high`) 기반 수동 판정이 함께 적용됩니다.  
   경계값 근처의 불필요한 반복 토글을 줄이기 위해 hysteresis 성격의 보정이 들어갑니다.

7. **Actuation**  
   최종 판단 결과에 따라 디지털 출력 또는 PWM 출력값을 계산해 MCU로 전달합니다.

8. **Web UI Broadcast**  
   대시보드용 데이터, 이상 상태, 액추에이터 상태, 시스템 리소스를 WebUI로 전송합니다.

---

## 🧠 이상 감지 로직 요약

### 1. Analog / I2C 센서
- 최근 데이터가 일정 수 이상 쌓이면(`min 15`) Isolation Forest 모델을 사용합니다.
- 모델은 센서별로 유지되며, 민감도 변경 시 재생성됩니다.
- 최신 포인트의 `decision_function()` 결과가 0보다 작으면 이상으로 판단합니다.
- 이상일 경우 최근 이동 평균과 비교해 방향을 `HIGH` 또는 `LOW`로 구분합니다.

### 2. Digital 센서
- 디지털 센서는 머신러닝을 사용하지 않습니다.
- 값이 설정된 트리거 상태와 일치하는지 규칙 기반으로 판단합니다.

### 3. Rule-based Override
- 임계값 기반 수동 판정이 AI 결과보다 우선 적용될 수 있습니다.
- `threshold_high` 초과 또는 `threshold_low` 미만 시 이상 상태로 판정합니다.
- margin 기반 보정을 통해 HIGH/LOW 상태가 급격히 튀지 않도록 구성되어 있습니다.

---

## 🗄️ 데이터베이스 스키마 설계 (Database Schema)

시스템은 **장치 설정용 관계형 저장소(SQLStore)**와 **센서 시계열 저장소(TimeSeriesStore)**를 함께 사용하는 구조입니다.

### 1. 센서 설정 테이블: `sensors`

| 컬럼명 | 데이터 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER | 센서 고유 식별자 |
| `name` | TEXT | 센서 논리 이름 |
| `protocol` | TEXT | `analog`, `digital`, `i2c` |
| `pin` | TEXT | 핀 번호 또는 I2C 주소 |
| `data_type` | TEXT | 예: Temperature, Humidity |
| `unit` | TEXT | 예: °C, %, lux |
| `sensitivity` | REAL | Isolation Forest contamination 값 |
| `threshold_low` | REAL | 하한 임계값 |
| `threshold_high` | REAL | 상한 임계값 |
| `multiplier` | REAL | 보정 배율 |
| `offset` | REAL | 보정 오프셋 |
| `profile_name` | TEXT | I2C 센서 프로필 이름 |
| `data_key` | TEXT | I2C 파싱 결과에서 추출할 키 |

### 2. 액추에이터 설정 테이블: `actuators`

| 컬럼명 | 데이터 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER | 액추에이터 고유 식별자 |
| `name` | TEXT | 액추에이터 논리 이름 |
| `control_type` | TEXT | `digital_out`, `pwm`, `virtual_*` |
| `pin` | TEXT | 물리 출력 핀 |
| `trigger_logic` | INTEGER | 저장소 호환 필드 |
| `linked_sensor_id` | INTEGER | 연동할 센서 ID |
| `normal_val` | INTEGER | 정상 상태 출력값 |
| `low_val` | INTEGER | LOW 이상 시 출력값 |
| `high_val` | INTEGER | HIGH 이상 시 출력값 |
| `trigger_dir` | TEXT | `HIGH`, `LOW`, `BOTH` |
| `extra_params` | TEXT | JSON 문자열 형태 부가 옵션 |

### 3. `extra_params` 예시
```json
{
  "delay": 3,
  "latch": true,
  "url": "https://example.com/webhook",
  "messenger": "discord"
}
```

### 4. 시계열 저장소
- 저장소: `TimeSeriesStore`
- 보관 기간: `retention_days=7`
- 최근 10분 기준 데이터 조회
- 2초 단위 평균 집계 데이터 제공 가능

---

## 🔀 컴포넌트 간 데이터 명세 (Data Structures)

### 1. MCU ↔ MPU 통신 인터페이스 (Bridge RPC)
Bridge RPC를 통해 MCU와 Python 레이어가 통신합니다.

- **아날로그/디지털 센서 응답**: 정수값 반환
- **I2C 바이트 읽기 응답**: 콤마(`,`)로 구분된 바이트 문자열 반환

예시:
```text
"56,128,0,23,91,12"
```

### 2. MPU ↔ Web UI 브로드캐스트 페이로드 예시
```json
{
  "Temperature_Sensor": {
    "rows": [
      ["19:34:21", 26.4],
      ["19:34:19", 26.2]
    ],
    "raw_rows": [
      ["19:34:21", 26.42],
      ["19:34:20", 26.18]
    ],
    "alert": true,
    "data_type": "Temperature",
    "unit": "°C",
    "protocol": "i2c",
    "score": -0.042183,
    "threshold_low": 15.0,
    "threshold_high": 35.0,
    "actuators": [
      {
        "id": 1,
        "name": "Cooling_Fan",
        "active": true,
        "control_type": "pwm",
        "pwm_val": 185,
        "latched": false
      }
    ]
  },
  "__sys_health__": {
    "cpu": 14.2,
    "ram": 48.7
  }
}
```

---

## 🔌 동적 I2C 센서 플러그인 아키텍처 (Driver Plugin System)

Raw2Insight의 핵심 확장 포인트는 I2C 센서 드라이버를 **파이썬 플러그인 구조**로 분리한 점입니다.

```text
[main.py]
   │
   ▼
[sensors/__init__.py] Loader
   │
   ├─► [sensors/aht20_driver.py]
   ├─► [sensors/other_sensor.py]
   └─► ... dynamically discovered profiles
```

### `BaseI2CSensor` 인터페이스
```python
class BaseI2CSensor:
    profile_name = "BASE"
    default_addr = "0x00"
    read_bytes = 0
    outputs = []

    def parse(self, data_bytes):
        raise NotImplementedError
```

### 동작 방식
- 런타임에 `sensors/` 디렉토리를 순회합니다.
- `BaseI2CSensor`를 상속한 클래스를 자동으로 로드합니다.
- 로드된 프로필은 WebUI에서 선택 가능한 I2C 드라이버 목록이 됩니다.
- `parse()`는 바이트 배열을 실제 물리값 딕셔너리로 변환합니다.

---

## 📂 프로젝트 구조 (Project Structure)

> 아래 구조는 **Arduino App Lab 프로젝트 패키징 형식 기준**입니다.

```text
📦 Raw2Insight
 ┣ 📂 assets/
 ┃ ┗ 📜 index.html
 ┣ 📂 python/
 ┃ ┣ 📜 main.py
 ┃ ┣ 📜 ai_manager.py
 ┃ ┣ 📜 comm_manager.py
 ┃ ┣ 📜 db_manager.py
 ┃ ┣ 📜 web_server.py
 ┃ ┣ 📜 requirements.txt
 ┃ ┗ 📂 sensors/
 ┃   ┗ 📜 __init__.py
 ┣ 📂 sketch/
 ┃ ┣ 📜 sketch.ino
 ┃ ┗ 📜 sketch.yaml
 ┗ 📜 app.yaml
```

### 파일 설명
- `assets/index.html`: 실시간 대시보드와 장치 설정 UI
- `python/main.py`: 메인 오케스트레이션 루프
- `python/ai_manager.py`: 이상 감지 모델 관리
- `python/comm_manager.py`: Bridge RPC 통신 레이어
- `python/db_manager.py`: SQL/시계열 저장소 관리
- `python/web_server.py`: WebUI 이벤트 및 브로드캐스트 처리
- `python/sensors/__init__.py`: I2C 센서 프로필 로더
- `sketch/sketch.ino`: MCU 하드웨어 I/O 및 Bridge provider
- `sketch/sketch.yaml`: Arduino App Lab용 Zephyr 빌드 프로필
- `app.yaml`: App Lab 브릭 및 앱 구성 정의

---

## 🔭 향후 확장 방향 (Future Work)
- 실제 센서 드라이버 확대 및 I2C 프로필 추가
- 이상 감지 모델 다변화
- 저장 데이터 리포트 및 내보내기 기능 추가
- 장기 추세 분석 및 알림 정책 고도화

---

## 👨‍💻 작성자 (Author)
- **Maker**: jihoonkimtech

## 📄 License
- **MIT License**