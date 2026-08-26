export interface User {
  id: number;
  email: string;
  name: string;
  created_at: string;
}

export interface Task {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  status: 'backlog' | 'today' | 'doing' | 'done';
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