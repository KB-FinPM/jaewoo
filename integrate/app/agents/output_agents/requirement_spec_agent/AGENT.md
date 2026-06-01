# Requirement Spec Output Agent

## 역할
요구사항 목록을 요구사항명세서 Excel 템플릿에 입력한다.

## 규칙
- 템플릿 파일 경로, 시트명, placeholder, 데이터 컬럼은 template/output_mapper.json 설정을 따른다.
- 소스에 시트명이나 컬럼 위치를 하드코딩하지 않는다.
- 산출물 파일명과 버전 증가는 공통 모듈 규칙을 사용한다.
