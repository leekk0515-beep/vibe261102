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
cp .env.example .env.local   # DATABASE_URL 에 Neon 연결 문자열을 넣습니다
npm run dev                  # http://localhost:3000
```

포트를 바꾸려면 `npm run dev -- --port 5175` 처럼 실행합니다.
저장소 루트의 `.claude/launch.json`에는 `demoweb`(포트 5175) 설정이 있어 Claude 미리보기에서 바로 띄울 수 있습니다.

프로덕션 빌드:

```bash
npm run build
npm start
```

## 데이터 저장 방식

[Neon](https://neon.tech)(서버리스 PostgreSQL)에 저장합니다. 연결 문자열은 `.env.local`의 `DATABASE_URL`에서 읽으며, 이 파일은 `.gitignore`에 포함되어 커밋되지 않습니다(`.env.example`만 커밋).

- 드라이버: `@neondatabase/serverless`의 HTTP 쿼리 함수(`neon()`). 커넥션 풀 관리가 필요 없고 서버리스 배포에도 그대로 쓸 수 있습니다.
- 스키마: 별도 마이그레이션 단계 없이, 서버가 처음 쿼리할 때 `posts`, `comments` 테이블과 인덱스를 `CREATE TABLE IF NOT EXISTS`로 만듭니다. 게시글이 하나도 없으면 안내용 글 3개를 넣습니다. 여러 프로세스가 동시에 시작해도 advisory lock으로 한 번만 실행됩니다.
- 댓글은 `post_id` 외래 키(`ON DELETE CASCADE`)로 묶여 있어 게시글을 지우면 함께 삭제됩니다.
- 검색은 `ILIKE`로 하며 `%`, `_`는 글자 그대로 검색되도록 이스케이프합니다.

초기화하려면 Neon 콘솔의 SQL Editor에서 `DROP TABLE comments, posts;`를 실행한 뒤 서버에 다시 접속하면 됩니다.

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
  lib/db.ts                  Neon(PostgreSQL) 저장소, 테이블 자동 생성
```

## 참고

- 로그인/권한 기능은 없습니다. 누구나 모든 글과 댓글을 수정·삭제할 수 있는 데모입니다.
- Next.js 16의 Cache Components가 켜져 있어, 데이터를 읽는 부분은 `<Suspense>` 안에서 요청마다 새로 렌더링됩니다.
