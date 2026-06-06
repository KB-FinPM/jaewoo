# CHANGELOG

## 기준

`sample_0531.zip` 기준으로 backend/FastAPI 통합 없이 standalone 구조에 기능을 재적용했습니다.

## 구조 변경 요약

```text
sample_0531/
├─ main.py (변경) process 인자 추가
├─ process.json (추가) 산출물 생성 제어
├─ PROCESS.md (변경) 처리 흐름 갱신
├─ README.md (변경) 실행/설정 설명 갱신
├─ CHANGELOG.md (추가) 변경내역 정리
├─ agents/ (추가) Agent 지침 분리
│  ├─ requirement_agent/AGENT.md (추가) 요구사항 지침
│  ├─ wbs_agent/AGENT.md (추가) WBS 지침
│  └─ storyboard_agent/AGENT.md (추가) 화면 지침
├─ template/
│  ├─ output_mapper.json (변경) Biz/WBS 설정 추가
│  ├─ wbs_template.json (추가) 공통 WBS 1~36
│  └─ deliverable_mapper.json (추가) 산출물 매핑
└─ modules/
   ├─ pipeline.py (변경) process 기반 제어
   ├─ extractor.py (변경) 프로젝트유형 반영
   ├─ wbs_generator.py (변경) 참고 WBS 규칙 반영
   ├─ screen_planner.py (변경) AGENT.md 반영
   ├─ excel_writer.py (변경) 출력 토큰 제한
   ├─ ppt_writer.py (변경) 출력 토큰 제한
   ├─ schemas.py (변경) Biz 필드 추가
   ├─ rag_service.py (변경) Biz 기준 RAG
   ├─ process_loader.py (추가) process 로딩
   ├─ agent_instruction.py (추가) AGENT.md 로딩
   ├─ project_profile.py (추가) 유형 자동분류
   └─ token_limiter.py (추가) 출력 제한
```

## 주요 변경

- 산출물 생성 여부를 `process.json`으로 제어
- `max_token`은 최종 output 생성에만 적용
- JSON 응답/복구에는 토큰 제한 미적용
- 인프라/개발/하이브리드 유형 지원
- 요구사항은 Biz요건명 중심으로 확장
- WBS No 1~36 공통 템플릿 추가
- No 37부터 Biz요건명 기준 WBS 생성
- 산출물 매핑 JSON 추가
- Agent별 `AGENT.md` 지침 로딩
- backend/FastAPI 구조 변경은 제외
