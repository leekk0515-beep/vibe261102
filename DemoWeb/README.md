# 데모 게시판 (DemoWeb)

Next.js(App Router) + TypeScript + shadcn/ui로 만든 웹 게시판입니다.

## 기능

- 게시글 목록(페이지당 10개, 페이지네이션), 상세, 작성, 수정, 삭제
- 댓글 작성/목록/삭제
- 제목 · 내용 · 제목+내용 검색
- 반응형 레이아웃, 라이트/다크/시스템 테마 전환
- 한국어 UI, 입력값 검증 메시지

## 실행 방법

Node.js 20 이상이 필요합니다(개발 환경: Node v24).

```bash
cd DemoWeb
npm install
npm run dev          # http://localhost:3000
```

포트를 바꾸려면 `npm run dev -- --port 5175` 처럼 실행합니다.
저장소 루트의 `.claude/launch.json`에는 `demoweb`(포트 5175) 설정이 있어 Claude 미리보기에서 바로 띄울 수 있습니다.

프로덕션 빌드:

```bash
npm run build
npm start
```

## 데이터 저장 방식

외부 DB 없이 **로컬 JSON 파일**(`DemoWeb/data/board.json`)에 저장합니다. 처음 실행하면 안내용 게시글 3개가 담긴 파일이 자동으로 만들어지고, 지우면 다시 초기화됩니다. 이 폴더는 `.gitignore`에 포함되어 있습니다.

이 방식을 고른 이유:

- `npm install` 후 바로 동작합니다. SQLite + Prisma처럼 네이티브 엔진 다운로드, 스키마 생성, 마이그레이션 단계가 필요 없습니다.
- 데이터가 사람이 읽을 수 있는 파일 하나라서 확인하고 초기화하기 쉽습니다.
- 데모 규모(수백~수천 건)에서는 매 요청마다 파일 전체를 읽어도 충분히 빠릅니다.

동시 쓰기로 데이터가 덮어써지지 않도록 쓰기를 프로세스 안에서 큐로 직렬화하고, 임시 파일에 쓴 뒤 교체(rename)합니다. 단, 서버 프로세스가 하나일 때를 전제로 하므로 여러 인스턴스로 배포하거나 데이터가 많아지면 `src/lib/db.ts`를 SQLite/PostgreSQL 등으로 바꾸면 됩니다(함수 시그니처는 그대로 두면 됩니다).

## 구조

```
src/
  app/
    page.tsx                 목록 + 검색 + 페이지네이션
    posts/new/page.tsx       글 작성
    posts/[id]/page.tsx      상세 + 댓글
    posts/[id]/edit/page.tsx 글 수정
    actions.ts               Server Actions(작성/수정/삭제/댓글, 입력 검증)
  components/                게시판 컴포넌트, components/ui 는 shadcn/ui
  lib/db.ts                  JSON 파일 저장소
```

## 참고

- 로그인/권한 기능은 없습니다. 누구나 모든 글과 댓글을 수정·삭제할 수 있는 데모입니다.
- Next.js 16의 Cache Components가 켜져 있어, 데이터를 읽는 부분은 `<Suspense>` 안에서 요청마다 새로 렌더링됩니다.
