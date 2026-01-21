import { Component, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { GeminiService, ArxivPaper } from './services/gemini.service';
import { PaperCardComponent } from './components/paper-card/paper-card.component';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { finalize } from 'rxjs';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface GroupedSection {
  year: number;
  papers: ArxivPaper[];
}

interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
}

declare var marked: any;

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, PaperCardComponent, HttpClientModule],
  templateUrl: './app.component.html',
})
export class AppComponent {
  private geminiService = inject(GeminiService);
  private http = inject(HttpClient);
  private sanitizer = inject(DomSanitizer);

  searchQuery = signal<string>('');
  results = signal<ArxivPaper[]>([]);
  resultsRaw = signal<ArxivPaper[]>([]);
  isLoading = signal<boolean>(false);
  hasSearched = signal<boolean>(false);

  // UI filters
  yearFrom = signal<number | null>(null);
  yearTo = signal<number | null>(null);
  sortBy = signal<'date' | 'relevance'>('date');
  sortOrder = signal<'asc' | 'desc'>('desc');

  // Suggestions
  suggestions = ['Quantum Computing', 'Large Language Models', 'Dark Matter', 'CRISPR'];

  // --- Chatbot State ---
  showChatbot = signal<boolean>(false);
  selectedPaper = signal<ArxivPaper | null>(null);
  chatMessage = signal<string>('');
  isBotThinking = signal<boolean>(false);
  thinkingStage = signal<string>('Thinking...');
  isFirstMessage = signal<boolean>(true);
  
  chatHistory = signal<ChatMessage[]>([
    { sender: 'bot', text: 'Hello! How can I assist you today? Select a paper to ask questions about it.' }
  ]);

  // --- New: Draggable & Resizable State ---
  chatWidth = signal<number>(450);
  // Position tracks the 'right' and 'bottom' distance in pixels
  chatPosition = signal({ x: 20, y: 20 });
  
  private isDragging = false;
  private isResizing = false;
  
  // Temp variables to calculate deltas
  private dragStartMouseX = 0;
  private dragStartMouseY = 0;
  private resizeStartMouseX = 0;
  private resizeStartWidth = 0;

  // --- Resizing Logic (Right edge towards left) ---
  // Note: Since the window is pinned to the right, dragging the right edge 
  // actually changes the 'right' position offset, while resizing the left edge 
  // changes the width. I will implement the resize handle on the LEFT side 
  // to allow expanding the window "towards the left".
  startResizing(event: MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isResizing = true;
    this.resizeStartMouseX = event.clientX;
    this.resizeStartWidth = this.chatWidth();
    document.body.style.cursor = 'ew-resize';
  }

  // --- Dragging Logic ---
  startDragging(event: MouseEvent) {
    // Don't drag if clicking buttons or input
    const target = event.target as HTMLElement;
    if (target.tagName === 'BUTTON' || target.tagName === 'TEXTAREA' || target.closest('button')) return;

    this.isDragging = true;
    this.dragStartMouseX = event.clientX;
    this.dragStartMouseY = event.clientY;
    document.body.style.cursor = 'grabbing';
  }

  @HostListener('window:mousemove', ['$event'])
  onMouseMove(event: MouseEvent) {
    if (this.isResizing) {
      // Calculate how much the mouse moved left/right
      // Moving mouse left (smaller clientX) increases width
      const deltaX = this.resizeStartMouseX - event.clientX;
      const newWidth = Math.max(320, Math.min(this.resizeStartWidth + deltaX, 1000));
      this.chatWidth.set(newWidth);
    }

    if (this.isDragging) {
      // Calculate delta movement
      const deltaX = this.dragStartMouseX - event.clientX;
      const deltaY = this.dragStartMouseY - event.clientY;

      this.chatPosition.update(pos => ({
        x: pos.x + deltaX,
        y: pos.y + deltaY
      }));

      // Update start values for next frame
      this.dragStartMouseX = event.clientX;
      this.dragStartMouseY = event.clientY;
    }
  }

  @HostListener('window:mouseup')
  onMouseUp() {
    this.isDragging = false;
    this.isResizing = false;
    document.body.style.cursor = 'default';
  }

  // --- Existing Logic ---
  async onSearch() {
    if (this.searchQuery().trim() === '') return;
    this.hasSearched.set(true);
    this.isLoading.set(true);
    this.results.set([]);
    const query = this.searchQuery();

    try {
      const newResults = await this.geminiService.searchPapers(query);
      this.results.set(newResults);
      this.resultsRaw.set(newResults);
    } catch (error) {
      console.error('Error fetching papers:', error);
    } finally {
      this.isLoading.set(false);
    }
  }

  onKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (this.showChatbot()) {
        this.sendMessage();
      } else {
        this.onSearch();
      }
    }
  }

  useSuggestion(topic: string) {
    this.searchQuery.set(topic);
    this.onSearch();
  }

  getGroupedSectionsSorted(): GroupedSection[] {
    const grouped = this.results().reduce<Record<number, ArxivPaper[]>>((acc, paper) => {
      const year = new Date(paper.date).getFullYear();
      if (!acc[year]) acc[year] = [];
      acc[year].push(paper);
      return acc;
    }, {});

    return Object.entries(grouped)
      .map(([year, papers]) => ({ year: +year, papers }))
      .sort((a, b) => b.year - a.year);
  }

  onPaperClick(paper: ArxivPaper) {
    this.selectedPaper.set(paper);
    this.showChatbot.set(true);
    this.isFirstMessage.set(true);
    this.chatHistory.set([
      { sender: 'bot', text: `You've selected "${paper.title}". What would you like to know?` }
    ]);
  }

  sendMessage() {
    const message = this.chatMessage().trim();
    const paper = this.selectedPaper();

    if (!message || this.isBotThinking() || !this.showChatbot()) return;

    this.chatHistory.update(history => [...history, { sender: 'user', text: message }]);
    this.chatMessage.set('');
    this.isBotThinking.set(true);

    // Start progress animation for first message
    if (this.isFirstMessage()) {
      this.startThinkingProgress();
    }

    const payload = {
      query: message,
      paperId: paper?.arxivId,
      pdfLink: paper ? `https://arxiv.org/pdf/${paper.arxivId}.pdf` : undefined
    };

    this.http.post<{ response: string }>('http://localhost:8000/question', payload)
      .pipe(finalize(() => {
        this.isBotThinking.set(false);
        this.thinkingStage.set('Thinking...');
        if (this.isFirstMessage()) {
          this.isFirstMessage.set(false);
        }
      }))
      .subscribe({
        next: (response) => {
          this.chatHistory.update(history => [...history, { sender: 'bot', text: response.response }]);
        },
        error: (err) => {
          console.error('API Error:', err);
          this.chatHistory.update(history => [...history, { sender: 'bot', text: 'Error encountered. Please try again.' }]);
        }
      });
  }

  private startThinkingProgress() {
    const stages = ['Getting paper...', 'Creating index...', 'Extracting data...'];
    let currentStage = 0;
    this.thinkingStage.set(stages[0]);

    const interval = setInterval(() => {
      currentStage++;
      if (currentStage < stages.length && this.isBotThinking()) {
        this.thinkingStage.set(stages[currentStage]);
      } else {
        clearInterval(interval);
      }
    }, 1000);
  }

  closeChatbot() {
    this.showChatbot.set(false);
    this.selectedPaper.set(null);
  }

  renderMarkdown(text: string): SafeHtml {
    if (typeof marked !== 'undefined') {
      const rawHtml = marked.parse(text);
      return this.sanitizer.bypassSecurityTrustHtml(rawHtml);
    }
    return text;
  }
}