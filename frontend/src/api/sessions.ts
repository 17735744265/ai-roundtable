import { apiGet, apiPost, apiDelete } from './client';
import type { SessionBrief, SessionDetail, PaginatedData, GuestGenerateResponse, GeneratedGuest } from '../types';

export function fetchGuests(): Promise<any[]> {
  return apiGet<any[]>('/experts');
}

export function generateGuests(topic: string, expertCount: number = 4): Promise<GuestGenerateResponse> {
  return apiPost<GuestGenerateResponse>('/discussion/generate-guests', { topic, expert_count: expertCount });
}

export function createSessionWithGuests(topic: string, generatedGuests: GeneratedGuest[]): Promise<SessionDetail> {
  return apiPost<SessionDetail>('/discussion/start', { topic, guest_ids: [], generated_guests: generatedGuests });
}

export function createSession(topic: string, guestIds: string[]): Promise<SessionDetail> {
  return apiPost<SessionDetail>('/discussion/start', { topic, guest_ids: guestIds, generated_guests: [] });
}

export function fetchSessions(page = 1, pageSize = 20, statusFilter = ''): Promise<PaginatedData<SessionBrief>> {
  const filter = statusFilter ? `&status_filter=${statusFilter}` : '';
  return apiGet<PaginatedData<SessionBrief>>(`/discussions?page=${page}&page_size=${pageSize}${filter}`);
}

export function fetchSession(id: string): Promise<SessionDetail> {
  return apiGet<SessionDetail>(`/discussions/${id}`);
}

export function deleteSession(id: string): Promise<void> {
  return apiDelete(`/discussions/${id}`);
}
