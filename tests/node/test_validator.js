const assert = require('assert');

function movingAverage(arr, window) {
  const res = new Array(arr.length).fill(null);
  let sum = 0;
  for (let i = 0; i < arr.length; i++) {
    sum += arr[i];
    if (i >= window) sum -= arr[i - window];
    if (i >= window - 1) res[i] = sum / window;
  }
  return res;
}

function testMovingAverage() {
  const arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const ma = movingAverage(arr, 3);
  assert.strictEqual(ma[0], null);
  assert.strictEqual(ma[1], null);
  assert.strictEqual(ma[2], 2);  // (1+2+3)/3
  assert.strictEqual(ma[3], 3);  // (2+3+4)/3
  console.log('✓ testMovingAverage');
}

function testSignalLogic() {
  // Test basic signal logic: UP if value > MA, DOWN otherwise
  const values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const mas = movingAverage(values, 3);
  const signals = values.map((v, i) => mas[i] === null ? 'NA' : (v > mas[i] ? 'UP' : 'DOWN'));
  assert.strictEqual(signals[0], 'NA');
  assert.strictEqual(signals[1], 'NA');
  assert.strictEqual(signals[2], 'UP');    // 3 > 2
  assert.strictEqual(signals[3], 'UP');    // 4 > 3
  assert.strictEqual(signals[4], 'UP');    // 5 > 4
  console.log('✓ testSignalLogic');
}

function testSmaNaPolicy() {
  // Ensure SMA window not filled => 'NA' signals
  const window = 20;
  const len = 25;
  const tlt = new Array(len).fill(100);
  const values = new Array(len).fill(1);
  const ma = movingAverage(values, window);
  const signals = values.map((v, i) => ma[i] === null ? 'NA' : (v > ma[i] ? 'UP' : 'DOWN'));
  for (let i = 0; i < window - 1; i++) {
    assert.strictEqual(signals[i], 'NA');
  }
  // index window-1 should be non-NA (first filled window)
  assert.notStrictEqual(signals[window - 1], 'NA');
  console.log('✓ testSmaNaPolicy');
}

if (require.main === module) {
  try {
    testMovingAverage();
    testSignalLogic();
    testSmaNaPolicy();
    console.log('\nAll Node tests passed');
  } catch (e) {
    console.error('Test failed:', e.message);
    process.exit(1);
  }
}
