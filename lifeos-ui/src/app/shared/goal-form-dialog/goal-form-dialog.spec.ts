import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GoalFormDialog } from './goal-form-dialog';

describe('GoalFormDialog', () => {
  let component: GoalFormDialog;
  let fixture: ComponentFixture<GoalFormDialog>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GoalFormDialog],
    }).compileComponents();

    fixture = TestBed.createComponent(GoalFormDialog);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
