import { apiGet } from './client';
import type { Guest } from '../types';

export function fetchGuests(): Promise<Guest[]> {
  return apiGet<Guest[]>('/experts');
}
