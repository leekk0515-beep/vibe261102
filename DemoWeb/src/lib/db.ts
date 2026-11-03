import "server-only";

import { neon, type NeonQueryFunction } from "@neondatabase/serverless";

/**
 * Neon(PostgreSQL) 저장소.
 *
 * `DATABASE_URL`(.env.local)로 연결하며, Neon의 HTTP 드라이버를 사용해 커넥션
 * 풀 관리 없이 요청마다 쿼리를 보냅니다. 첫 쿼리 때 테이블이 없으면 만들고,
 * 게시글이 하나도 없으면 안내용 글을 넣습니다.
 */

export type Post = {
  id: string;
  title: string;
  content: string;
  author: string;
  createdAt: string;
  updatedAt: string;
};

export type Comment = {
  id: string;
  postId: string;
  author: string;
  content: string;
  createdAt: string;
};

export type PostSummary = Post & { commentCount: number };

export type SearchField = "all" | "title" | "content";

type Row = Record<string, unknown>;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

let client: NeonQueryFunction<false, false> | undefined;
let ready: Promise<void> | undefined;

function sql() {
  if (!client) {
    const url = process.env.DATABASE_URL;
    if (!url) {
      throw new Error(
        "DATABASE_URL이 설정되지 않았습니다. DemoWeb/.env.local 에 Neon 연결 문자열을 넣어 주세요.",
      );
    }
    client = neon(url);
  }
  return client;
}

/** 테이블 생성과 초기 데이터 입력을 프로세스당 한 번만 수행합니다. */
async function db() {
  const q = sql();
  ready ??= q
    .transaction([
      // 여러 서버 프로세스가 동시에 초기화해도 시드가 한 번만 들어가게 합니다.
      q`SELECT pg_advisory_xact_lock(724100)`,
      q`CREATE TABLE IF NOT EXISTS posts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          title text NOT NULL,
          content text NOT NULL,
          author text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        )`,
      q`CREATE INDEX IF NOT EXISTS posts_created_at_idx ON posts (created_at DESC)`,
      q`CREATE TABLE IF NOT EXISTS comments (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          post_id uuid NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
          author text NOT NULL,
          content text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now()
        )`,
      q`CREATE INDEX IF NOT EXISTS comments_post_id_idx ON comments (post_id, created_at)`,
      q`INSERT INTO posts (title, content, author, created_at, updated_at)
        SELECT s.title, s.content, '관리자', now() - s.ago, now() - s.ago
        FROM (VALUES
          ('게시판에 오신 것을 환영합니다',
           E'Next.js App Router와 shadcn/ui로 만든 데모 게시판입니다.\\n\\n글을 작성하고, 수정하고, 삭제하고, 댓글을 남겨 보세요.',
           interval '3 minutes'),
          ('검색 기능 사용법',
           '상단 검색창에서 제목, 내용 또는 제목+내용으로 게시글을 찾을 수 있습니다.',
           interval '2 minutes'),
          ('다크 모드를 지원합니다',
           '우측 상단의 테마 버튼으로 라이트/다크/시스템 모드를 전환할 수 있습니다.',
           interval '1 minute')
        ) AS s(title, content, ago)
        WHERE NOT EXISTS (SELECT 1 FROM posts)`,
    ])
    .then(() => undefined)
    .catch((err) => {
      // 일시적인 연결 오류 뒤에 다시 시도할 수 있게 합니다.
      ready = undefined;
      throw err;
    });
  await ready;
  return q;
}

function iso(v: unknown) {
  return new Date(v as string | Date).toISOString();
}

function toPost(r: Row): Post {
  return {
    id: r.id as string,
    title: r.title as string,
    content: r.content as string,
    author: r.author as string,
    createdAt: iso(r.created_at),
    updatedAt: iso(r.updated_at),
  };
}

function toComment(r: Row): Comment {
  return {
    id: r.id as string,
    postId: r.post_id as string,
    author: r.author as string,
    content: r.content as string,
    createdAt: iso(r.created_at),
  };
}

export async function listPosts({
  query = "",
  field = "all",
  page = 1,
  pageSize = 10,
}: {
  query?: string;
  field?: SearchField;
  page?: number;
  pageSize?: number;
}) {
  const q = await db();
  const term = query.trim();
  // ILIKE 패턴 문자(%, _)와 이스케이프 문자는 글자 그대로 검색합니다.
  const pattern = `%${term.replace(/[\\%_]/g, (c) => `\\${c}`)}%`;
  const byTitle = field !== "content";
  const byContent = field !== "title";
  const where = q`(${term} = ''
    OR (${byTitle} AND title ILIKE ${pattern})
    OR (${byContent} AND content ILIKE ${pattern}))`;

  const [{ count }] = (await q`SELECT count(*)::int AS count FROM posts WHERE ${where}`) as {
    count: number;
  }[];
  const total = count;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(Math.max(1, page), totalPages);

  const rows = (await q`
    SELECT p.*,
      (SELECT count(*)::int FROM comments c WHERE c.post_id = p.id) AS comment_count
    FROM posts p
    WHERE ${where}
    ORDER BY p.created_at DESC, p.id
    LIMIT ${pageSize} OFFSET ${(current - 1) * pageSize}`) as Row[];

  const items: PostSummary[] = rows.map((r) => ({
    ...toPost(r),
    commentCount: r.comment_count as number,
  }));

  return { items, total, page: current, totalPages, pageSize };
}

export async function getPost(id: string) {
  if (!UUID.test(id)) return null;
  const q = await db();
  const [posts, comments] = await Promise.all([
    q`SELECT * FROM posts WHERE id = ${id}` as Promise<Row[]>,
    q`SELECT * FROM comments WHERE post_id = ${id} ORDER BY created_at, id` as Promise<Row[]>,
  ]);
  if (posts.length === 0) return null;
  return { post: toPost(posts[0]), comments: comments.map(toComment) };
}

export async function createPost(input: Pick<Post, "title" | "content" | "author">) {
  const q = await db();
  const rows = (await q`
    INSERT INTO posts (title, content, author)
    VALUES (${input.title}, ${input.content}, ${input.author})
    RETURNING *`) as Row[];
  return toPost(rows[0]);
}

export async function updatePost(
  id: string,
  input: Pick<Post, "title" | "content" | "author">,
) {
  if (!UUID.test(id)) return null;
  const q = await db();
  const rows = (await q`
    UPDATE posts
    SET title = ${input.title}, content = ${input.content},
        author = ${input.author}, updated_at = now()
    WHERE id = ${id}
    RETURNING *`) as Row[];
  return rows[0] ? toPost(rows[0]) : null;
}

/** 댓글은 외래 키의 ON DELETE CASCADE로 함께 삭제됩니다. */
export async function deletePost(id: string) {
  if (!UUID.test(id)) return false;
  const q = await db();
  const rows = (await q`DELETE FROM posts WHERE id = ${id} RETURNING id`) as Row[];
  return rows.length > 0;
}

export async function addComment(
  postId: string,
  input: Pick<Comment, "author" | "content">,
) {
  if (!UUID.test(postId)) return null;
  const q = await db();
  // 게시글이 없으면 아무것도 넣지 않고 null을 돌려줍니다.
  const rows = (await q`
    INSERT INTO comments (post_id, author, content)
    SELECT id, ${input.author}, ${input.content} FROM posts WHERE id = ${postId}
    RETURNING *`) as Row[];
  return rows[0] ? toComment(rows[0]) : null;
}

export async function deleteComment(id: string) {
  if (!UUID.test(id)) return false;
  const q = await db();
  const rows = (await q`DELETE FROM comments WHERE id = ${id} RETURNING id`) as Row[];
  return rows.length > 0;
}
