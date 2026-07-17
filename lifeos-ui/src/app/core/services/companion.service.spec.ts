import { TestBed } from '@angular/core/testing';

import { Companion } from './companion';

describe('Companion', () => {
  let service: Companion;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Companion);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
