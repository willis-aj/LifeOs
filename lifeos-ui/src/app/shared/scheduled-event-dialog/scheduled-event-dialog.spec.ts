import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScheduledEventDialog } from './scheduled-event-dialog';

describe('ScheduledEventDialog', () => {
  let component: ScheduledEventDialog;
  let fixture: ComponentFixture<ScheduledEventDialog>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScheduledEventDialog],
    }).compileComponents();

    fixture = TestBed.createComponent(ScheduledEventDialog);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
