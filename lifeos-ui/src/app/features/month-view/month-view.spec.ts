import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MonthView } from './month-view';

describe('MonthView', () => {
  let component: MonthView;
  let fixture: ComponentFixture<MonthView>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MonthView],
    }).compileComponents();

    fixture = TestBed.createComponent(MonthView);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
