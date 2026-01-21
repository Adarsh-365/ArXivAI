import { Injectable } from '@angular/core';

export interface ArxivPaper {
  title: string;
  authors: string[];
  summary: string;
  arxivId: string;
  date?: string;
  category: string;
}

@Injectable({ providedIn: 'root' })
export class GeminiService {
  // Using a local FastAPI backend running on localhost:8000
  private baseUrl = 'http://localhost:8000';

  constructor() {}

  private toStringSafe(v: any): string {
    if (v === null || v === undefined) return '';
    if (typeof v === 'string') return v;
    if (typeof v === 'number' || typeof v === 'boolean') return String(v);
    if (Array.isArray(v)) return v.map((x) => this.toStringSafe(x)).join(', ');
    if (typeof v === 'object') {
      if ('title' in v && typeof v.title === 'string') return v.title;
      if ('name' in v && typeof v.name === 'string') return v.name;
      try {
        return JSON.stringify(v);
      } catch (_) {
        return String(v);
      }
    }
    return String(v);
  }

  async searchPapers(query: string): Promise<ArxivPaper[]> {
    if (!query || !query.trim()) return [];

    try {
      const resp = await fetch(`${this.baseUrl}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      if (!resp.ok) {
        const text = await resp.text();
        console.error('Local API error', resp.status, text);
        return [];
      }

      const data = await resp.json();

      // Support two response shapes from FastAPI:
      // 1) { answer: ['http://arxiv.org/pdf/2006.08233v3', ...] }
      // 2) [ { title, authors, summary, arxivId, category }, ... ]
      if (Array.isArray(data)) {
        // Map array items (e.g., serialized `arxiv.Result`) into ArxivPaper
        return (data as any[]).map((item) => {
          const rawTitle = item && (item.title || item['title']) ? item.title || item['title'] : '';
          const title = this.toStringSafe(rawTitle);
          const authors = Array.isArray(item?.authors)
            ? item.authors.map((a: any) => this.toStringSafe(a))
            : [];
          const summary = this.toStringSafe(item && (item.summary || item.description || ''));

          const pdf = item && (item.pdf_url || item.pdf || item['pdf_url'] || item.source_url) ? (item.pdf_url || item.pdf || item['pdf_url'] || item.source_url) : '';
          let arxivId = '';
          try {
            if (pdf) {
              const parts = pdf.split('/');
              arxivId = (parts[parts.length - 1] || '').replace(/\.pdf$/i, '');
            } else if (item && item.entry_id) {
              const parts = (item.entry_id + '').split('/');
              arxivId = parts[parts.length - 1] || (item.entry_id + '');
            } else if (item && item.id) {
              const parts = (item.id + '').split('/');
              arxivId = parts[parts.length - 1] || (item.id + '');
            }
          } catch (e) {
            arxivId = '';
          }

          const category = item && (item.primary_category || (Array.isArray(item.categories) ? item.categories[0] : '')) ? (item.primary_category || (Array.isArray(item.categories) ? item.categories[0] : '')) : '';

            // Normalize arxivId further: strip URL prefixes and leading 'arXiv:' etc.
            let normId = arxivId || '';
            normId = normId.replace(/^https?:\/\//, '');
            normId = normId.replace(/^arxiv:\s*/i, '');
            normId = normId.replace(/^abs\//i, '');
            normId = normId.replace(/\.pdf$/i, '');

            const dateVal = (item && (item.date || item.published || item.updated)) ? (item.date || item.published || item.updated) : '';

            return {
              title: title || pdf || normId || this.toStringSafe(item),
              authors,
              summary,
              arxivId: normId,
              date: this.toStringSafe(dateVal),
              category
            } as ArxivPaper;
        });
      }

      if (data && data.answer) {
        // Case A: answer is an array of URLs
        if (Array.isArray(data.answer)) {
          const urls: string[] = data.answer;
          return urls.map((u) => {
            try {
              const parts = u.split('/');
              let last = parts[parts.length - 1] || '';
              last = last.replace(/\.pdf$/i, '');
              return {
                title: `arXiv:${last}`,
                authors: [],
                summary: '',
                arxivId: last,
                category: ''
              } as ArxivPaper;
            } catch (e) {
              return {
                title: u,
                authors: [],
                summary: '',
                arxivId: u,
                category: ''
              } as ArxivPaper;
            }
          });
        }

        // Case B: answer is an object mapping URL -> metadata
        if (typeof data.answer === 'object' && !Array.isArray(data.answer)) {
          const entries = Object.entries(data.answer) as [string, any][];
          return entries.map(([key, val]) => {
            const title = this.toStringSafe((val && val.title) ? val.title : key);
            const pdf = (val && val.pdf_url) ? val.pdf_url : '';
            let arxivId = '';
            try {
              const src = pdf || key;
              const parts = src.split('/');
              arxivId = (parts[parts.length - 1] || '').replace(/\.pdf$/i, '');
            } catch (e) {
              arxivId = key;
            }

            return {
              title,
              authors: (val && Array.isArray(val.authors)) ? val.authors.map((a: any) => this.toStringSafe(a)) : [],
              summary: this.toStringSafe(val && val.summary ? val.summary : ''),
              arxivId,
              date: this.toStringSafe(val && (val.date || val.published) ? (val.date || val.published) : ''),
              category: this.toStringSafe(val && val.category ? val.category : '')
            } as ArxivPaper;
          });
        }
      }

      return [];
    } catch (err) {
      console.error('Fetch error to local API:', err);
      return [];
    }
  }
}