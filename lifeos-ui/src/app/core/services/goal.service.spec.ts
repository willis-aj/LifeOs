import { TestBed } from '@angular/core/testing';

import { Goal } from './goal';

describe('Goal', () => {
  let service: Goal;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Goal);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
