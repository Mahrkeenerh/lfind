## **Project Summary: LFind – A Natural Language File Finder**

### **Overview and Goals**

*LFind* is a file search tool designed to help users locate files and directories across very large repositories (potentially millions of entries) using a combination of classical metadata filtering and advanced semantic search methods. The primary goals are:

1. **Traditional Filtering:**  
   Allow users to quickly narrow down results using standard file attributes such as:
   - Directory (or absolute path) filtering (e.g., search within a given directory recursively)
   - File extensions (e.g., PDF, DOCX)
   - Date ranges (e.g., modified after a specific date)
   - File sizes

2. **Semantic Search:**  
   Enable further refinement of the filtered results using:
   - **Vector-based similarity search (via FAISS):** Compute embeddings from file content, titles, or summaries to capture semantic meaning.
   - **LLM-assisted search:** Use large language models (LLMs) to interpret natural language queries and match them against the candidate set, optionally integrating with semantic vector search.

3. **Ease of Installation & Efficiency:**  
   - Use SQLite as a serverless, lightweight metadata store.
   - Use FAISS for fast, local vector similarity searches.
   - Ensure the overall system is efficient even with large databases and requires minimal extra infrastructure.

---

## **Architecture & Design**

### **1. Metadata Management**

- **Database:**  
  We use SQLite (via Python’s built-in `sqlite3` module) to store file metadata. This database holds all the necessary details for each file or directory:
  - **Fields include:**  
    - `id`: Unique identifier (INTEGER PRIMARY KEY AUTOINCREMENT)
    - `name`: File name  
    - `absolute_path`: Full file path (used for recursive filtering with a `LIKE` query)  
    - `type`: Indicates if the entry is a file or a directory  
    - `extension`: File extension  
    - `size`: File size  
    - `created_at` and `modified_at`: Timestamps  
    - `last_indexed_at`: When the file was last updated in the database  
    - `embedding_id`: An integer linking to the corresponding vector embedding in FAISS (if applicable)  
    - `seen`: A flag used during scheduled updates to track whether the file was encountered in the current scan

- **Single-Pass Update Mechanism:**  
  Instead of maintaining a separate cached file tree and then doing two passes (one for updating and one for cleaning), our design uses a scheduled function that:
  - **Resets all `seen` flags** to 0.
  - **Walks through the file system** (using something like `os.walk`), and for each file/directory:
    - Calls a function (`touch_file`) that compares the current file’s stats (size, modification time) with what's in the database.
    - If the file is new or updated, the record is inserted or updated and the `seen` flag is set to 1.
    - If the record is already up-to-date, only the `seen` flag is set.
  - **After the walk,** a function (`delete_missing_files`) removes all records with `seen = 0` (files that no longer exist).

### **2. Semantic Search with FAISS**

- **Vector Embeddings:**  
  For files that are candidates for semantic search, we compute vector embeddings (e.g., from file content summaries) using a chosen model. These embeddings capture the semantic meaning of the file.

- **FAISS Index:**  
  The embeddings are stored in a FAISS index using an `IndexIDMap`, which maps each embedding to the unique ID from the SQLite metadata store. This allows us to perform fast similarity searches. When a query is made:
  - **Two approaches are considered:**
    - **Limited Index Approach:** Retrieve embeddings for the candidate files (filtered by metadata) and build a temporary FAISS index for a very selective search.
    - **Post-Filtering Approach:** Run a similarity search on the full FAISS index and then filter the returned results based on the metadata candidate set.
  - The choice between these strategies can be tuned based on the selectivity of the metadata filters.

### **3. LLM Integration**

- **Natural Language Query Processing:**  
  In addition to vector similarity search, the system supports searches using large language models. For example, an LLM may be prompted with candidate file summaries (obtained via metadata filtering) to determine which files best match a natural language query.

- **Filtered LLM Search:**  
  This LLM search is applied on the candidate set (as determined by metadata filtering), ensuring that even semantic search via LLMs respects the user-specified criteria (directory, date, size, etc.).

### **4. User Interface**

- **Console/CLI:**  
  A simple console UI allows users to:
  - Enter search criteria (directory, extension, date, size)
  - View initial results from metadata filtering
  - Optionally refine the results with a semantic similarity query (using FAISS and/or LLMs)
  - Display final matching file paths along with relevant metadata

---

## **Implementation Roadmap**

1. **Data Acquisition & Metadata Extraction:**
   - **File System Walk:**  
     Implement a scheduled process that uses `os.walk` (or a similar mechanism) to iterate through the file system.
   - **Database Population:**  
     For each file/directory, build a metadata dictionary and call the `touch_file` method to update or insert the record.  
     Use a `seen` flag in the database to track which records are up-to-date.
   - **Cleanup:**  
     After scanning, call a function to delete all records where `seen` remains 0, indicating that these files were not found.

2. **Metadata Storage Implementation:**
   - Develop the `DatabaseManager` class (as detailed in the provided code), including methods for:
     - Initialization (`_init_database`)
     - Inserting/updating records (`upsert_file` and `touch_file`)
     - Resetting the `seen` flag (`reset_seen_flags`)
     - Deleting missing files (`delete_missing_files`)
     - Querying files by criteria (`get_files_by_criteria`)
     - Retrieving mappings and individual records

3. **FAISS Vector Index Integration:**
   - Compute embeddings for relevant file content.
   - Create and maintain a FAISS index that maps embeddings to file IDs.
   - Develop functions to perform vector similarity searches, either by building a temporary index for a filtered candidate set or by post-filtering results from the full index.

4. **LLM-Based Search Integration:**
   - Extend the existing LLM search functionality to allow natural language queries on top of the metadata-filtered candidate set.
   - Ensure that the LLM prompts include only the relevant context (e.g., file names or summaries) from the filtered set.

5. **User Interface (CLI):**
   - Develop a console interface that guides the user through:
     - Inputting filter criteria.
     - Displaying metadata-filtered results.
     - Allowing additional semantic query input.
     - Displaying final file paths and details.

6. **Testing, Benchmarking, and Documentation:**
   - Write unit and integration tests for each module (metadata handling, FAISS operations, LLM integration).
   - Benchmark the performance of both similarity search approaches (re-indexing versus post-filtering) and optimize accordingly.
   - Prepare documentation that explains installation (using SQLite and FAISS, no external servers needed), configuration, and usage instructions.

7. **Final Integration & Deployment:**
   - Integrate all components into a single cohesive application.
   - Package the project as a Python package or executable for easy distribution and installation.
   - Ensure clear configuration options for scheduled updates, filtering criteria, and search modes.

---

## **Conclusion**

*LFind* aims to provide a fast, flexible, and easy-to-install file search tool that combines the power of metadata filtering (via SQLite) with semantic search techniques (via FAISS and LLMs). The current design leverages a single-pass scheduled update that walks through the file system, updates the database records with a "seen" flag, and then cleans up records for deleted files—all while keeping the installation simple and the system efficient for large-scale file repositories.
