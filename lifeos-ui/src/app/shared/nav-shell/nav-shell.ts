import { Component } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { PlayerContextService } from '../../core/state/player-context.service';
import { ThemeService } from '../../core/services/theme.service';

interface NavLink {
  path: string;
  label: string;
  icon: string;
}

const NAV_LINKS: NavLink[] = [
  { path: '/home', label: 'Home', icon: 'home' },
  { path: '/day', label: 'Day', icon: 'view_day' },
  { path: '/month', label: 'Month', icon: 'calendar_month' },
  { path: '/backlog', label: 'Backlog', icon: 'inventory_2' },
  { path: '/goals', label: 'Goals', icon: 'flag' },
  { path: '/modes', label: 'Modes', icon: 'tune' },
  { path: '/settings', label: 'Settings', icon: 'settings' },
];

/** App shell: top nav bar (route links + theme toggle + player switcher)
 * wrapping a router-outlet. Nav links are hidden until a player is
 * selected, since every route except /players needs a current player. */
@Component({
  selector: 'app-nav-shell',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
  ],
  templateUrl: './nav-shell.html',
  styleUrl: './nav-shell.scss',
})
export class NavShell {
  readonly navLinks = NAV_LINKS;

  constructor(
    readonly playerContext: PlayerContextService,
    readonly theme: ThemeService,
    private readonly router: Router,
  ) {}

  toggleTheme(): void {
    this.theme.toggle();
  }

  switchPlayer(): void {
    this.playerContext.clearPlayer();
    this.router.navigate(['/players']);
  }
}
