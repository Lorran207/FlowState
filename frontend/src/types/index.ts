export interface User {
  id: number;
  email: string;
  name: string;
  github_username: string | null;
  created_at: string;
}

export type TaskStatus = 'backlog' | 'today' | 'doing' | 'done';

export interface Task {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  position: number;
  created_at: string;
  completed_at: string | null;
}

export interface StudySession {
  id: number;
  user_id: number;
  task_id: number | null;
  started_at: string;
  ended_at: string | null;
  duration_min: number | null;
  completed: boolean;
}

export interface JournalEntry {
  id: number;
  user_id: number;
  session_id: number;
  content: string;
  created_at: string;
}

export interface DashboardData {
  stats: {
    xp_total: number;
    level: number;
    streak: number;
    longest_streak: number;
    last_active_date: string | null;
  };
  recent_sessions: StudySession[];
  recent_tasks: Task[];
  weekly_minutes: number;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface GitHubStatus {
  connected: boolean;
  username: string | null;
  commit_count: number;
}

export interface GitHubCommit {
  id: number;
  user_id: number;
  sha: string;
  message: string;
  repo_name: string;
  url: string;
  committed_at: string;
}

export type FeedItemType = 'pomodoro' | 'journal' | 'commit';

export interface FeedItem {
  type: FeedItemType;
  title: string;
  description: string | null;
  url: string | null;
  timestamp: string;
}

export interface HeatmapDay {
  date: string;
  count: number;
  minutes: number;
}

export interface SyncResult {
  new_commits: number;
  total_commits: number;
}