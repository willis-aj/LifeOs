import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DayDetailDialog } from './day-detail-dialog';

describe('DayDetailDialog', () => {
  let component: DayDetailDialog;
  let fixture: ComponentFixture<DayDetailDialog>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DayDetailDialog],
    }).compileComponents();

    fixture = TestBed.createComponent(DayDetailDialog);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
