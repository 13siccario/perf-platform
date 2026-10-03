import http from 'k6/http';
import { Counter } from 'k6/metrics';

const BASE = __ENV.TARGET_URL || 'http://localhost:8000';
const STOCK = 10;
const sales = new Counter('sales_ok');

http.setResponseCallback(http.expectedStatuses(200, 409));

export const options = {
  scenarios: {
    rush: { executor: 'per-vu-iterations', vus: 100, iterations: 1, maxDuration: '30s' },
  },
  thresholds: {
    // Exactly STOCK purchases may succeed; more means we oversold.
    sales_ok: [`count==${STOCK}`],
  },
};

export function setup() {
  http.post(`${BASE}/admin/stock/1/${STOCK}`);
}

export default function () {
  const res = http.post(`${BASE}/buy/1`);
  if (res.status === 200) sales.add(1);
}
