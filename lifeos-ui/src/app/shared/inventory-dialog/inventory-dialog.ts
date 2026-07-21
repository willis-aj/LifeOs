import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';

import { InventoryItem, InventoryService } from '../../core/services/inventory.service';
import { NotifyService } from '../../core/services/notify.service';

export interface InventoryDialogData {
  playerId: string;
}

/** Read-only loot inventory, opened from the Home dashboard's "Inventory"
 * chip. Mirrors the item list already shown on the Settings page, just
 * scoped to its own dialog for a one-click glance from Home. */
@Component({
  selector: 'app-inventory-dialog',
  imports: [MatDialogModule, MatButtonModule, MatChipsModule, MatProgressSpinnerModule, MatTooltipModule],
  templateUrl: './inventory-dialog.html',
  styleUrl: './inventory-dialog.scss',
})
export class InventoryDialog implements OnInit {
  private readonly inventoryService = inject(InventoryService);
  private readonly notify = inject(NotifyService);
  private readonly dialogRef = inject(MatDialogRef<InventoryDialog>);
  readonly data = inject<InventoryDialogData>(MAT_DIALOG_DATA);

  readonly loading = signal(true);
  readonly items = signal<InventoryItem[]>([]);

  ngOnInit(): void {
    this.inventoryService.getInventory(this.data.playerId).subscribe({
      next: (items) => {
        this.items.set(items);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  close(): void {
    this.dialogRef.close();
  }
}
