/**
 * Parse CSV text into an array of records.
 * Supports quoted fields, escaped quotes, commas, and newlines inside quotes.
 * The first row is treated as the header row.
 */
export function parseCSV(text) {
  if (typeof text !== "string") throw new TypeError("CSV input must be a string.");

  const source = text.replace(/^\uFEFF/, "");
  if (source.trim() === "") return { headers: [], rows: [] };

  const records = [];
  let record = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];

    if (char === '"') {
      if (quoted && next === '"') {
        field += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      record.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") index += 1;
      record.push(field);
      records.push(record);
      record = [];
      field = "";
    } else {
      field += char;
    }
  }

  if (quoted) throw new Error("The CSV contains an unclosed quoted field.");

  record.push(field);
  records.push(record);

  while (records.length && records.at(-1).every((value) => value === "")) records.pop();
  if (!records.length) return { headers: [], rows: [] };

  const headers = records.shift().map((header, index) => {
    const cleaned = header.trim();
    return cleaned || `Column ${index + 1}`;
  });

  const rows = records.map((values) => headers.map((_, index) => values[index] ?? ""));
  return { headers, rows };
}

export function getDatasetStats(rows, columnCount) {
  const emptyCells = rows.reduce(
    (total, row) => total + row.filter((value) => value.trim() === "").length,
    0,
  );

  return { rowCount: rows.length, columnCount, emptyCells };
}

/**
 * Return duplicate groups using exact cell values and column order.
 * Each group includes the original row and its occurrence count.
 */
export function findDuplicateRows(rows) {
  const seen = new Map();
  const duplicates = [];

  for (const row of rows) {
    const key = JSON.stringify(row);
    const existing = seen.get(key);

    if (existing) {
      existing.count += 1;
    } else {
      seen.set(key, { row, count: 1 });
    }
  }

  for (const entry of seen.values()) {
    if (entry.count > 1) duplicates.push(entry);
  }

  return duplicates;
}

/**
 * Count blank or whitespace-only cells in each column.
 */
export function getMissingValuesByColumn(headers, rows) {
  return headers.map((header, columnIndex) => ({
    column: header,
    missing: rows.reduce(
      (total, row) => total + (row[columnIndex] == null || row[columnIndex].trim() === "" ? 1 : 0),
      0,
    ),
  }));
}

export function searchRows(rows, query) {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery) return rows;

  return rows.filter((row) =>
    row.some((value) => value.toLocaleLowerCase().includes(normalizedQuery)),
  );
}
