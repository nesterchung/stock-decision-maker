const fs = require('fs');
const { parse } = require('csv-parse');

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { prices: null, canonical: null, window: 20, compareMetrics: false };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--prices' || a === '-p') out.prices = args[++i];
    else if (a === '--canonical' || a === '-c') out.canonical = args[++i];
    else if (a === '--window' || a === '-w') out.window = parseInt(args[++i], 10);
    else if (a === '--compare-metrics') {
      const val = args[++i];
      out.compareMetrics = val === 'true' || val === true;
    }
  }
  if (!out.prices || !out.canonical) {
    console.error('Usage: node validator.js --prices <prices.csv> --canonical <canonical.ndjson> [--window 20] [--compare-metrics false|true]');
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
      // Validate required columns exist
      const requiredColumns = ['date', 'XLE', 'TLT', 'XLK', 'XLU', 'SPY'];
      const firstRow = results[0] || {};
      const missingColumns = requiredColumns.filter(col => !(col in firstRow));
      
      if (missingColumns.length > 0) {
        reject(new Error(`Missing required columns in CSV: ${missingColumns.join(', ')}`));
        return;
      }
      
      // Parse numeric fields and validate data types
      const parsed = [];
      for (const r of results) {
        const parsedRow = {
          date: r['date'],
          XLE: parseFloat(r['XLE']),
          TLT: parseFloat(r['TLT']),
          XLK: parseFloat(r['XLK']),
          XLU: parseFloat(r['XLU']),
          SPY: parseFloat(r['SPY']),
        };
        
        // Validate numeric values
        const numericFields = ['XLE', 'TLT', 'XLK', 'XLU', 'SPY'];
        for (const field of numericFields) {
          if (isNaN(parsedRow[field])) {
            reject(new Error(`Non-numeric value found in column ${field} on date ${r['date']}: ${r[field]}`));
            return;
          }
        }
        
        parsed.push(parsedRow);
      }
      
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

function computeSignals(rows, window, compareMetrics = false) {
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

    const result = { date, signals: { energy, rates, tech, utilities } };
    
    if (compareMetrics) {
      result.metrics = {
        energy: { value: rs_energy[i], sma: ma_energy[i] },
        rates: { value: tlt[i], sma: ma_tlt[i] },
        tech: { value: rs_tech[i], sma: ma_tech[i] },
        utilities: { value: rs_util[i], sma: ma_util[i] }
      };
    }
    
    out.push(result);
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
    } catch (_e) {
      console.error('Failed to parse canonical line:', l);
    }
  }
  return map;
}

function compareMetrics(canonicalMetrics, computedMetrics, epsilon = 1e-8) {
  const mismatches = [];
  
  for (const signalName of Object.keys(canonicalMetrics)) {
    const can = canonicalMetrics[signalName];
    const comp = computedMetrics[signalName];
    
    // Compare values
    if (can.value !== null && comp.value !== null) {
      if (Math.abs(can.value - comp.value) > epsilon) {
        mismatches.push({ 
          field: `${signalName}_value`, 
          expected: can.value, 
          actual: comp.value 
        });
      }
    } else if (can.value !== comp.value) {
      mismatches.push({ 
        field: `${signalName}_value`, 
        expected: can.value, 
        actual: comp.value 
      });
    }
    
    // Compare SMAs
    if (can.sma !== null && comp.sma !== null) {
      if (Math.abs(can.sma - comp.sma) > epsilon) {
        mismatches.push({ 
          field: `${signalName}_sma`, 
          expected: can.sma, 
          actual: comp.sma 
        });
      }
    } else if (can.sma !== comp.sma) {
      mismatches.push({ 
        field: `${signalName}_sma`, 
        expected: can.sma, 
        actual: comp.sma 
      });
    }
  }
  
  return mismatches;
}

async function main() {
  try {
    const args = parseArgs();
    const rows = await readCSV(args.prices);
    // ensure sorted by date lexicographically
    rows.sort((a, b) => a.date.localeCompare(b.date));

    const computed = computeSignals(rows, args.window, args.compareMetrics);
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
          mismatches.push({ date, field: f, canonical_value: b, computed_value: a });
        }
      }
      
      // Compare metrics if requested
      if (args.compareMetrics && can.metrics && rec.metrics) {
        const metricMismatches = compareMetrics(can.metrics, rec.metrics);
        for (const mm of metricMismatches) {
          mismatches.push({ 
            date, 
            field: mm.field, 
            canonical_value: mm.expected, 
            computed_value: mm.actual 
          });
        }
      }
    }

    if (mismatches.length === 0) {
      console.log('VALIDATOR: OK — no mismatches found');
      process.exit(0);
    } else {
      console.error('VALIDATOR: MISMATCHES FOUND:', mismatches.length);
      for (const m of mismatches.slice(0, 20)) {
        console.error(`${m.date},${m.field},${m.canonical_value},${m.computed_value}`);
      }
      if (mismatches.length > 20) console.error('...');
      process.exit(1);
    }
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(2);
  }
}

if (require.main === module) main();
