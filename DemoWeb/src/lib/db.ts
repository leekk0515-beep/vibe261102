import "server-only";

import { randomUUID } from "node:crypto";
import { existsSync } from "node:fs";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";

/**
 * 로컬 JSON 파일 저장소.
 *
 * 외부 DB·네이티브 바이너리·마이그레이션 없이 `npm install` 직후 바로 동작하도록
 * `data/board.json` 한 파일에 게시글과 댓글을 저장합니다. 쓰기는 프로세스 내
 * 큐로 직렬화하고(최초 시드 생성 포함) 임시 파일에 쓴 뒤 rename 하여 파일이
 * 깨지지 않게 합니다.
 * 단일 서버 프로세스용 데모 저장소이며, 다중 인스턴스·대용량에는 맞지 않습니다.
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

type Data = { posts: Post[]; comments: Comment[] };

export type SearchField = "all" | "title" | "content";

const DATA_DIR = path.join(process.cwd(), "data");
const DATA_FILE = path.join(DATA_DIR, "board.json");

let queue: Promise<unknown> = Promise.resolve();

function seed(): Data {
  const now = Date.now();
  const posts: Post[] = [
    {
      title: "게시판에 오신 것을 환영합니다",
      content:
        "Next.js App Router와 shadcn/ui로 만든 데모 게시판입니다.\n\n글을 작성하고, 수정하고, 삭제하고, 댓글을 남겨 보세요.",
      author: "관리자",
    },
    {
      title: "검색 기능 사용법",
      content:
        "상단 검색창에서 제목, 내용 또는 제목+내용으로 게시글을 찾을 수 있습니다.",
      author: "관리자",
    },
    {
      title: "다크 모드를 지원합니다",
      content: "우측 상단의 테마 버튼으로 라이트/다크/시스템 모드를 전환할 수 있습니다.",
      author: "관리자",
    },
  ].map((p, i) => {
    const at = new Date(now - (3 - i) * 60_000).toISOString();
    return { ...p, id: randomUUID(), createdAt: at, updatedAt: at };
  });
  return { posts, comments: [] };
}

async function load(): Promise<Data> {
  if (!existsSync(DATA_FILE)) {
    const data = seed();
    await save(data);
    return data;
  }
  return JSON.parse(await readFile(DATA_FILE, "utf8")) as Data;
}

async function save(data: Data) {
  await mkdir(DATA_DIR, { recursive: true });
  const tmp = `${DATA_FILE}.${randomUUID()}.tmp`;
  await writeFile(tmp, JSON.stringify(data, null, 2), "utf8");
  await rename(tmp, DATA_FILE);
}

/**
 * 모든 파일 접근을 하나의 큐로 직렬화합니다. 읽기-수정-쓰기가 서로의 변경을
 * 덮어쓰지 않고, 첫 요청들이 동시에 시드 파일을 만들다 충돌하지 않게 합니다.
 */
function serialize<T>(fn: () => Promise<T>): Promise<T> {
  const run = queue.then(fn);
  queue = run.catch(() => undefined);
  return run;
}

function mutate<T>(fn: (data: Data) => T): Promise<T> {
  return serialize(async () => {
    const data = await load();
    const result = fn(data);
    await save(data);
    return result;
  });
}

function read(): Promise<Data> {
  return serialize(load);
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
  const { posts, comments } = await read();
  const q = query.trim().toLowerCase();

  const filtered = posts
    .filter((p) => {
      if (!q) return true;
      const inTitle = p.title.toLowerCase().includes(q);
      const inContent = p.content.toLowerCase().includes(q);
      if (field === "title") return inTitle;
      if (field === "content") return inContent;
      return inTitle || inContent;
    })
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));

  const total = filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(Math.max(1, page), totalPages);
  const items: PostSummary[] = filtered
    .slice((current - 1) * pageSize, current * pageSize)
    .map((p) => ({
      ...p,
      commentCount: comments.filter((c) => c.postId === p.id).length,
    }));

  return { items, total, page: current, totalPages, pageSize };
}

export async function getPost(id: string) {
  const { posts, comments } = await read();
  const post = posts.find((p) => p.id === id);
  if (!post) return null;
  return {
    post,
    comments: comments
      .filter((c) => c.postId === id)
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt)),
  };
}

export function createPost(input: Pick<Post, "title" | "content" | "author">) {
  return mutate((data) => {
    const now = new Date().toISOString();
    const post: Post = { ...input, id: randomUUID(), createdAt: now, updatedAt: now };
    data.posts.push(post);
    return post;
  });
}

export function updatePost(
  id: string,
  input: Pick<Post, "title" | "content" | "author">,
) {
  return mutate((data) => {
    const post = data.posts.find((p) => p.id === id);
    if (!post) return null;
    Object.assign(post, input, { updatedAt: new Date().toISOString() });
    return post;
  });
}

export function deletePost(id: string) {
  return mutate((data) => {
    const before = data.posts.length;
    data.posts = data.posts.filter((p) => p.id !== id);
    data.comments = data.comments.filter((c) => c.postId !== id);
    return data.posts.length < before;
  });
}

export function addComment(
  postId: string,
  input: Pick<Comment, "author" | "content">,
) {
  return mutate((data) => {
    if (!data.posts.some((p) => p.id === postId)) return null;
    const comment: Comment = {
      ...input,
      id: randomUUID(),
      postId,
      createdAt: new Date().toISOString(),
    };
    data.comments.push(comment);
    return comment;
  });
}

export function deleteComment(id: string) {
  return mutate((data) => {
    const before = data.comments.length;
    data.comments = data.comments.filter((c) => c.id !== id);
    return data.comments.length < before;
  });
}
