import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ArxivPaper } from '../../services/gemini.service';

@Component({
  selector: 'app-paper-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './paper-card.component.html',
})
export class PaperCardComponent {
  paper = input.required<ArxivPaper>();

  getPdfUrl(id: string): string {
    return `https://arxiv.org/pdf/${id}.pdf`;
  }
  
  openPdf(event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    const pdfUrl = this.getPdfUrl(this.paper().arxivId);
    window.open(pdfUrl, '_blank');
  }
  
  getNowDate(): string {
      return new Date().toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }
}