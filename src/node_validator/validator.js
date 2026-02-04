const fs = require('fs');
const path = require('path');
const { parse } = require('csv-parse');

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { prices: null, canonical: null, window: 20 };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--prices' || a === '-p') out.prices = args[++i];
    else if (a === '--canonical' || a === '-c') out.canonical = args[++i];
    else if (a === '--window' || a === '-w') out.window = parseInt(args[++i], 10);
  }
  if (!out.prices || !out.canonical) {
    console.error('Usage: node validator.js --prices <prices.csv> --canonical <canonical.ndjson> [--window 20]');
    process.exit(2);
  }
  return out;
}

function readCSV(p) {
  const content = fs.readFileSync(p, 'utf8');
  
  return new Promise((resolve, reject) => {
    const results = [];
    
    parse(content, {
      columns: true,
      skip_empty_lines: true,
      trim: true,
      relax_column_count: true, // handle extra columns
      relax_quotes: true, // handle quoted fields more flexibly
    })
    .on('data', (data) => {
      results.push(data);
    })
    .on('end', () => {
      // parse numeric fields and keep date strings
      const parsed = results.map(r => {
        return {
          date: r['date'],
          XLE: parseFloat(r['XLE']),
          TLT: parseFloat(r['TLT']),
          XLK: parseFloat(r['XLK']),
          XLU: parseFloat(r['XLU']),
          SPY: parseFloat(r['SPY']),
        };
      });
      resolve(parsed);
    })
    .on('error', (error) => {
      reject(error);
    });
  });
}

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

function computeSignals(rows, window) {
  // assume rows are in chronological order
  const rs_energy = rows.map(r => r.XLE / r.SPY);
  const rs_tech = rows.map(r => r.XLK / r.SPY);
  const rs_util = rows.map(r => r.XLU / r.SPY);
  const tlt = rows.map(r => r.TLT);

  const ma_energy = movingAverage(rs_energy, window);
  const ma_tech = movingAverage(rs_tech, window);
  const ma_util = movingAverage(rs_util, window);
  const ma_tlt = movingAverage(tlt, window);

  const out = [];
  for (let i = 0; i < rows.length; i++) {
    const date = rows[i].date;
    const energy = (ma_energy[i] == null) ? 'NA' : (rs_energy[i] > ma_energy[i] ? 'UP' : 'DOWN');
    const rates = (ma_tlt[i] == null) ? 'NA' : (tlt[i] < ma_tlt[i] ? 'UP' : 'DOWN');
    const tech = (ma_tech[i] == null) ? 'NA' : (rs_tech[i] > ma_tech[i] ? 'UP' : 'DOWN');
    const utilities = (ma_util[i] == null) ? 'NA' : (rs_util[i] > ma_util[i] ? 'UP' : 'DOWN');

    out.push({ date, signals: { energy, rates, tech, utilities } });
  }
  return out;
}

function readCanonical(p) {
  const txt = fs.readFileSync(p, 'utf8').trim();
  const lines = txt.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
  const map = new Map();
  for (const l of lines) {
    try {
      const obj = JSON.parse(l);
      map.set(obj.date, obj);
    } catch (e) {
      console.error('Failed to parse canonical line:', l);
    }
  }
  return map;
}

async function main() {
  try {
    const args = parseArgs();
    const rows = await readCSV(args.prices);
    // ensure sorted by date lexicographically
    rows.sort((a, b) => a.date.localeCompare(b.date));

    const computed = computeSignals(rows, args.window);
    const canonical = readCanonical(args.canonical);

    const mismatches = [];
    for (const rec of computed) {
      const date = rec.date;
      if (!canonical.has(date)) {
        mismatches.push({ date, reason: 'missing_in_canonical' });
        continue;
      }
      const can = canonical.get(date);
      const fields = ['energy', 'rates', 'tech', 'utilities'];
      for (const f of fields) {
        const a = rec.signals[f];
        const b = can.signals[f];
        if (a !== b) {
          mismatches.push({ date, field: f, expected: b, actual: a });
        }
      }
    }

    if (mismatches.length === 0) {
      console.log('VALIDATOR: OK — no mismatches found');
      process.exit(0);
    } else {
      console.error('VALIDATOR: MISMATCHES FOUND:', mismatches.length);
      for (const m of mismatches.slice(0, 20)) console.error(JSON.stringify(m));
      if (mismatches.length > 20) console.error('...');
      process.exit(1);
    }
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(2);
  }
}

if (require.main === module) main();
