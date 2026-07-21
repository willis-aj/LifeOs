import {
  AfterViewChecked,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
  inject,
  input,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ChatService } from '../../core/services/chat.service';
import { NotifyService } from '../../core/services/notify.service';
import { ChatMessage } from '../../core/models/chat.model';

/** A single unified chat surface where more than one persona can speak:
 * the plain-spoken "LifeOS System" (structural confirmations/errors) and
 * the warm "Self-Care Agent" (conversation, goal-setting, scaffolding),
 * alongside the user's own turns. Bubble styling is driven entirely by
 * `message.speaker` (see chat-panel.scss) so adding a future persona is
 * just a new CSS class, not a new component. */
@Component({
  selector: 'app-chat-panel',
  imports: [FormsModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './chat-panel.html',
  styleUrl: './chat-panel.scss',
})
export class ChatPanel implements OnInit, AfterViewChecked {
  readonly playerId = input.required<string>();

  @ViewChild('scrollback') private scrollback?: ElementRef<HTMLDivElement>;
  private shouldScroll = false;

  private readonly chatService = inject(ChatService);
  private readonly notify = inject(NotifyService);

  readonly messages = signal<ChatMessage[]>([]);
  readonly loading = signal(true);
  readonly sending = signal(false);
  draftText = '';

  ngOnInit(): void {
    this.chatService.getHistory(this.playerId()).subscribe({
      next: (response) => {
        this.messages.set(response.messages);
        this.loading.set(false);
        this.shouldScroll = true;
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll && this.scrollback) {
      this.scrollback.nativeElement.scrollTop = this.scrollback.nativeElement.scrollHeight;
      this.shouldScroll = false;
    }
  }

  send(): void {
    const text = this.draftText.trim();
    if (!text || this.sending()) return;

    this.sending.set(true);
    this.draftText = '';

    this.chatService.sendMessage(this.playerId(), text).subscribe({
      next: (response) => {
        this.messages.update((current) => [...current, ...response.messages]);
        this.sending.set(false);
        this.shouldScroll = true;
      },
      error: (err) => {
        this.sending.set(false);
        this.notify.error(err);
      },
    });
  }

  onEnter(event: Event): void {
    event.preventDefault();
    this.send();
  }
}
