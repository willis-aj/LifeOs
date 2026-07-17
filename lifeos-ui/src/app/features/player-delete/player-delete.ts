import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';

export interface PlayerDeleteData {
  playerName: string;
}

/** Confirmation dialog for permanently deleting a player and all their
 * data. Closes with `true` if the user confirmed, `false`/undefined
 * otherwise - the caller (player-select) is responsible for actually
 * calling PlayerService.deletePlayer() after a `true` result. */
@Component({
  selector: 'app-player-delete',
  imports: [MatDialogModule, MatButtonModule],
  templateUrl: './player-delete.html',
  styleUrl: './player-delete.scss',
})
export class PlayerDelete {
  constructor(
    private readonly dialogRef: MatDialogRef<PlayerDelete, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: PlayerDeleteData,
  ) {}

  confirm(): void {
    this.dialogRef.close(true);
  }

  cancel(): void {
    this.dialogRef.close(false);
  }
}
