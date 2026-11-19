import { describe, expect, it } from "vitest";
import { getDatasetStats, parseCSV, searchRows } from "../src/csv.js";

describe("parseCSV", () => {
  it("parses headers and rows", () => {
    expect(parseCSV("name,city\nAda,London")).toEqual({
      headers: ["name", "city"],
      rows: [["Ada", "London"]],
    });
  });

  it("supports commas and newlines inside quoted fields", () => {
    expect(parseCSV('name,note\nAda,"London, UK"\nGrace,"First line\nSecond line"').rows).toEqual([
      ["Ada", "London, UK"],
      ["Grace", "First line\nSecond line"],
    ]);
  });

  it("supports escaped quote characters", () => {
    expect(parseCSV('name,quote\nAda,"She said ""hello"""').rows).toEqual([
      ["Ada", 'She said "hello"'],
    ]);
  });

  it("fills missing trailing values and names blank columns", () => {
    expect(parseCSV("name,\nAda").rows).toEqual([["Ada", ""]]);
    expect(parseCSV("name,\nAda").headers).toEqual(["name", "Column 2"]);
  });

  it("handles a byte order mark and empty input", () => {
    expect(parseCSV("\uFEFFname\nAda").headers).toEqual(["name"]);
    expect(parseCSV("")).toEqual({ headers: [], rows: [] });
  });

  it("rejects unclosed quoted fields", () => {
    expect(() => parseCSV('name,note\nAda,"unfinished')).toThrow(/unclosed/i);
  });
});

describe("dataset helpers", () => {
  it("counts empty cells", () => {
    expect(getDatasetStats([["Ada", ""], ["", "Paris"]], 2)).toEqual({
      rowCount: 2,
      columnCount: 2,
      emptyCells: 2,
    });
  });

  it("searches every cell without case sensitivity", () => {
    expect(searchRows([["Ada", "London"], ["Grace", "New York"]], "LON")).toEqual([
      ["Ada", "London"],
    ]);
  });

  it("returns all rows for an empty search", () => {
    const rows = [["Ada"], ["Grace"]];
    expect(searchRows(rows, "  ")).toBe(rows);
  });
});
