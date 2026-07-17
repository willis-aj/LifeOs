import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DayView } from './day-view';

describe('DayView', () => {
  let component: DayView;
  let fixture: ComponentFixture<DayView>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DayView],
    }).compileComponents();

    fixture = TestBed.createComponent(DayView);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
