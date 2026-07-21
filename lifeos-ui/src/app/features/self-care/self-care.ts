import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';

import { PlayerContextService } from '../../core/state/player-context.service';
import { ChatPanel } from '../../shared/chat-panel/chat-panel';

/** Full-page home for the Self-Care Agent's chat interface - the
 * conversational counterpart to the passive nudges shown in
 * shared/self-care-panel on the Home dashboard. */
@Component({
  selector: 'app-self-care',
  imports: [ChatPanel],
  templateUrl: './self-care.html',
  styleUrl: './self-care.scss',
})
export class SelfCare implements OnInit {
  private readonly playerContext = inject(PlayerContextService);
  private readonly router = inject(Router);

  readonly playerId = this.playerContext.playerId;

  ngOnInit(): void {
    if (!this.playerContext.hasPlayer()) {
      this.router.navigate(['/players']);
    }
  }
}
