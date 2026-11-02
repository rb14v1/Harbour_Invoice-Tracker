import { apiClient } from "./client";
import type { Client, Paginated } from "../types";

export interface ClientInput {
  name: string;
  email: string;
  phone?: string;
  notes?: string;
}

export function listClients() {
  return apiClient.get<Paginated<Client>>("/clients/", { params: { page_size: 100 } });
}

export function createClient(data: ClientInput) {
  return apiClient.post<Client>("/clients/", data);
}

export function updateClient(id: number, data: ClientInput) {
  return apiClient.put<Client>(`/clients/${id}/`, data);
}

export function deleteClient(id: number) {
  return apiClient.delete(`/clients/${id}/`);
}
