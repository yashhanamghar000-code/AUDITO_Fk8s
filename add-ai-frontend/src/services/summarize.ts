import { api } from "./api";

export interface SummarizeResponse {
  status: string;
  file_id: string;
  summary: string;
}

export const summarizeService = {
  summarize: (fileId: string) => {
    const form = new FormData();
    form.append("file_id", fileId);
    return api.post<SummarizeResponse>("/api/summarize", form);
  },
};
