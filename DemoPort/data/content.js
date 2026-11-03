// 사이트 콘텐츠 데이터 (PRD FR-5)
// 이 파일만 수정하면 화면 내용이 갱신됩니다.
// [확정 필요] 표시가 붙은 항목은 실제 정보로 교체하세요.
window.SITE_CONTENT = {
  profile: {
    name: "홍길동", // [확정 필요] 표시할 이름
    title: "Batch Process Software Engineer", // [확정 필요] 직함
    tagline: "화학 공정을 이해하는 소프트웨어 개발자",
    summary:
      "회분식 화학합성 공정의 레시피 관리, 장비 제어, 데이터 수집·분석 프로그램을 설계하고 개발합니다.",
    email: "lkkkk0515@gmail.com",
    resumeUrl: "", // [확정 필요] 예: "assets/resume.pdf" — 비워두면 버튼이 숨겨집니다.
    links: [
      { label: "GitHub", url: "" }, // [확정 필요]
      { label: "LinkedIn", url: "" } // [확정 필요]
    ]
  },

  about: {
    paragraphs: [
      "반응기 앞에서 일어나는 일을 이해하고, 그것을 신뢰할 수 있는 소프트웨어로 옮기는 일을 합니다. 회분식 화학합성 공정에서 레시피 설계부터 장비 제어, 배치 기록까지 이어지는 흐름 전체를 다뤄 왔습니다.",
      "현장 운전자와 공정 엔지니어가 실제로 쓰는 도구를 만드는 것을 중요하게 생각합니다. 같은 레시피는 언제나 같은 결과를 내야 하고, 모든 배치는 추적 가능해야 합니다."
    ],
    principles: [
      { title: "재현성", text: "같은 레시피는 같은 결과를. 공정 단계와 파라미터를 명확히 모델링합니다." },
      { title: "추적성", text: "모든 배치의 이력·이벤트·데이터를 남겨 문제를 거슬러 올라갈 수 있게 합니다." },
      { title: "안전 우선", text: "인터록과 예외 상황을 먼저 설계하고, 정상 흐름은 그다음에 만듭니다." }
    ]
  },

  expertise: [
    {
      icon: "reactor",
      title: "배치 공정 제어 · 레시피 관리",
      text: "ISA-88 개념 기반의 레시피·단계(Phase) 모델링과 배치 실행 엔진 설계."
    },
    {
      icon: "plug",
      title: "반응기 장비 연동",
      text: "PLC, OPC UA, Modbus 등을 통한 온도·압력·교반·투입 장비 제어 및 상태 수집."
    },
    {
      icon: "chart",
      title: "공정 데이터 모니터링",
      text: "실시간 트렌드, 알람, 대시보드로 공정 상태를 한눈에 파악할 수 있도록 시각화."
    },
    {
      icon: "record",
      title: "배치 기록 · 이력 추적",
      text: "전자 배치 기록(EBR), 감사 추적(Audit Trail) 등 품질·규제 대응을 위한 데이터 관리."
    },
    {
      icon: "flask",
      title: "합성 실험 · 생산 자동화",
      text: "실험실 규모부터 생산 규모까지, 반복 작업을 자동화하고 실험 데이터를 체계화."
    }
  ],

  // [확정 필요] 실제 사용 기술로 교체
  skills: [
    { category: "Languages", items: ["C#", "Python", "C++", "SQL"] },
    { category: "Frameworks", items: [".NET", "WPF", "ASP.NET Core", "Qt"] },
    { category: "Industrial Protocols", items: ["OPC UA", "Modbus TCP/RTU", "RS-232/485"] },
    { category: "Data", items: ["SQL Server", "PostgreSQL", "InfluxDB"] },
    { category: "Tools", items: ["Git", "Docker", "Visual Studio", "TIA Portal"] },
    { category: "Domain", items: ["ISA-88", "GMP", "21 CFR Part 11", "P&ID"] }
  ],

  // [확정 필요] 공개 가능한 프로젝트로 교체 (기밀 공정 조건·고객사명은 제외)
  projects: [
    {
      title: "배치 레시피 관리 및 실행 시스템",
      period: "2024 – 2025",
      summary: "다품종 회분식 합성 라인을 위한 레시피 편집기와 배치 실행 엔진.",
      problem: "레시피가 문서와 수기로 관리되어 버전 혼선과 운전 편차가 발생했습니다.",
      role: "아키텍처 설계, 실행 엔진 및 레시피 편집기 개발",
      solution: "ISA-88 기반 단계 모델로 레시피를 구조화하고, 승인 워크플로와 버전 관리를 도입했습니다. 실행 엔진은 각 단계를 상태 머신으로 처리합니다.",
      results: ["레시피 버전 혼선 0건", "배치 준비 시간 단축", "운전 이력 자동 기록"],
      tags: ["C#", "WPF", "SQL Server", "ISA-88"],
      image: ""
    },
    {
      title: "반응기 실시간 모니터링 대시보드",
      period: "2023",
      summary: "여러 반응기의 온도·압력·교반 속도를 실시간으로 수집하고 시각화.",
      problem: "운전자가 장비별 HMI를 따로 확인해야 해서 이상 징후를 늦게 발견했습니다.",
      role: "데이터 수집 서비스 및 웹 대시보드 개발",
      solution: "OPC UA로 장비 데이터를 통합 수집해 시계열 DB에 저장하고, 웹 대시보드에서 트렌드와 알람을 제공했습니다.",
      results: ["반응기 상태 통합 화면 제공", "알람 대응 시간 단축"],
      tags: ["Python", "OPC UA", "InfluxDB", "ASP.NET Core"],
      image: ""
    },
    {
      title: "전자 배치 기록(EBR) 모듈",
      period: "2022",
      summary: "종이 배치 기록을 대체하는 전자 기록 및 감사 추적 모듈.",
      problem: "수기 기록으로 인한 누락과 검토 지연이 반복되었습니다.",
      role: "데이터 모델 설계, 전자서명·감사 추적 기능 개발",
      solution: "단계별 입력 검증과 전자서명을 적용하고, 모든 변경을 감사 추적 테이블에 기록했습니다.",
      results: ["기록 누락 감소", "배치 검토 기간 단축"],
      tags: ["C#", "PostgreSQL", "21 CFR Part 11"],
      image: ""
    },
    {
      title: "투입 장비 Modbus 연동 드라이버",
      period: "2021",
      summary: "원료 정량 투입 펌프·저울을 제어하는 통신 드라이버와 시뮬레이터.",
      problem: "장비마다 통신 방식이 달라 연동 코드가 중복되고 테스트가 어려웠습니다.",
      role: "드라이버 공통 인터페이스 설계, 시뮬레이터 개발",
      solution: "장비 추상화 계층을 만들고 Modbus TCP/RTU 구현을 분리했습니다. 실제 장비 없이 테스트할 수 있는 시뮬레이터를 함께 제공했습니다.",
      results: ["신규 장비 연동 기간 단축", "장비 없는 통합 테스트 가능"],
      tags: ["C++", "Modbus TCP/RTU", "Qt"],
      image: ""
    }
  ],

  // [확정 필요] 실제 경력으로 교체
  experience: [
    {
      period: "2022 – 현재",
      org: "OO케미칼",
      role: "공정 소프트웨어 개발자",
      text: "회분식 합성 공정용 레시피·배치 실행 시스템 및 모니터링 솔루션 개발."
    },
    {
      period: "2019 – 2022",
      org: "OO오토메이션",
      role: "제어 소프트웨어 엔지니어",
      text: "화학·제약 플랜트 장비 연동 드라이버 및 HMI 개발."
    }
  ]
};
