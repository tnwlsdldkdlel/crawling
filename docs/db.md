# 📄 Product Requirements Document (PRD) - Yarn/Pattern Recommendation Service

## 1. Product Goal

The goal is to build a service that recommends popular **patterns** or **yarns** used by other users, based on Naver Blog data, when a user searches for a pattern or yarn.

---

## 2. Database Design (Supabase/Postgres)

Data Crawling Source: **Naver Blog**

### A. Yarns Table (Yarn Information)

| Field Name     | Data Type | Description                              | Constraints |
| :------------- | :-------- | :--------------------------------------- | :---------- |
| `id`           | `uuid`    | Unique identifier for each yarn          | Primary Key |
| `name`         | `text`    | Yarn name (e.g., Hera Cotton)            | Not Null    |
| `manufacturer` | `text`    | Manufacturer/Brand                       |             |
| `color`        | `text`    | Yarn color information (e.g., Red, Blue) |             |
| `url`          | `text`    | URL for yarn information/purchase        |             |

### B. Patterns Table (Pattern Information)

| Field Name   | Data Type | Description                                | Constraints |
| :----------- | :-------- | :----------------------------------------- | :---------- |
| `id`         | `uuid`    | Unique identifier for each pattern         | Primary Key |
| `name`       | `text`    | Pattern name (e.g., Four Seasons Cardigan) | Not Null    |
| `source_url` | `text`    | Original blog/purchase URL for the pattern |             |

### C. PatternYarnLink Table (Pattern-Yarn Relationship)

This table stores the relationship where a specific pattern and yarn are **mentioned together**. The count of records in this table serves as the key recommendation metric.

| Field Name   | Data Type | Description                            | Constraints            |
| :----------- | :-------- | :------------------------------------- | :--------------------- |
| `id`         | `uuid`    | Unique identifier for the relationship | Primary Key            |
| `pattern_id` | `uuid`    | ID from the `Patterns` table           | Foreign Key (Patterns) |
| `yarn_id`    | `uuid`    | ID from the `Yarns` table              | Foreign Key (Yarns)    |

---

## 3. Core Logic & Features

### A. Data Collection and Storage Strategy

1.  **Crawling:** Crawl new postings from Naver Blogs to extract **pattern names** and **yarn names**.
2.  **Data Normalization:** Check if the extracted names exist in the tables; if not, create new records.
3.  **Relationship Storage:** When **Pattern A** and **Yarn B** are mentioned together in one blog post, a **new record** for the corresponding `(pattern_id, yarn_id)` pair is inserted into the `PatternYarnLink` table. (The cumulative number of these records acts as the recommendation weight.)

### B. Recommendation Logic

The recommendation uses the record count in the `PatternYarnLink` table as the **Implicit Use Count**.

| Scenario               | Search Query          | Recommendation Target | Recommendation Logic                                                                                                                                               |
| :--------------------- | :-------------------- | :-------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pattern Search**     | Specific `pattern_id` | **Yarns**             | Aggregate all `yarn_id`s linked to the `pattern_id` in the `PatternYarnLink` table, and recommend the yarn list sorted by **most frequent `yarn_id` count**.       |
| **Yarn Search**        | Specific `yarn_id`    | **Patterns**          | Aggregate all `pattern_id`s linked to the `yarn_id` in the `PatternYarnLink` table, and recommend the pattern list sorted by **most frequent `pattern_id` count**. |
| **Overall Popularity** | -                     | **Yarn or Pattern**   | Provide an overall popularity list sorted by the **highest total mention count** of `yarn_id` or `pattern_id` in the `PatternYarnLink` table.                      |

---

### 4. User Interface (UI - Example)

- **Pattern Detail Page:** Add a section titled "**Yarns Frequently Used Together**" to display top recommended yarns.
- **Yarn Detail Page:** Add a section titled "**Patterns Often Made with This Yarn**" to display top recommended patterns.
