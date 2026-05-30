/*
  사용방법
  1. 크롬브라우저 사용
  2. 금융 연수원 사이트 접속 > AI 리터러시 eBook > F12 또는 개발자모드 열기
  3. 아래 함수 입력 window.downloadEbookImages = .....
  4. downloadEbookImages() 함수 실행. 수행후 파일 잘 생성되는지 확인
  5. 종료 원할 경우 화면 refresh 또는 맨 하단의 함수 초기화 실행
*/

window.downloadEbookImages = async () => {
    // 1. smcimg1_ 로 시작하는 id를 가진 모든 이미지 요소 선택
    const images = document.querySelectorAll('image[id^="smcimg1_"]');
    
    if (images.length === 0) {
        console.error("대상 이미지를 찾을 수 없습니다. E-Book이 화면에 로드되었는지 확인하세요.");
        return;
    }

    console.log(`총 ${images.length}개의 이미지를 발견했습니다. 다운로드를 시작합니다...`);

    for (let i = 0; i < images.length; i++) {
        const img = images[i];
        const imgSrc = img.getAttribute("xlink:href");
        const imgId = img.id;

        try {
            // 2. Blob 데이터를 fetch하여 응답 받기
            const response = await fetch(imgSrc);
            const blob = await response.blob();
            
            // 3. 다운로드를 위한 임시 링크 생성
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            // 파일명 설정 (id값 활용)
            a.download = `${imgId}.jpeg`; 
            
            document.body.appendChild(a);
            a.click();
            
            // 4. 메모리 정리를 위해 객체 URL 해제 및 요소 제거
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            console.log(`성공: ${imgId} 다운로드 완료`);
            
            // 서버 부하 및 브라우저 차단을 방지하기 위한 짧은 지연 시간
            await new Promise(resolve => setTimeout(resolve, 300));
            
        } catch (error) {
            console.error(`실패: ${imgId}를 처리하는 중 오류 발생`, error);
        }
    }

    setTimeout(function() {
    	nextbtnClick();
	    setTimeout(function() {
	    	downloadEbookImages();
	    }, 1000);
    }, 1000);
    
    console.log("모든 작업이 완료되었습니다.");
};

// 함수 초기화
// window.downloadEbookImages = null;