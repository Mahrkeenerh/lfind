# **Project Overview and Roadmap**

## **Project Overview**

**Project Name:**  
*LFind* – A Natural Language File Finder with Multi-Stage Filtering and Semantic Search

**Goal:**  
Develop a robust file search tool that empowers users to locate files (and directories) using both traditional metadata filters and advanced semantic methods. The tool combines:

- **Traditional Filtering:**  
  Using metadata (absolute paths, file extensions, dates, sizes, etc.) stored in a lightweight SQLite database.

- **Vector-Based Similarity Search:**  
  Utilizing FAISS to perform rapid semantic searches over file embeddings (derived from file titles, content, or summaries).

- **LLM-Assisted Search:**  
  Employing large language models (LLMs) to interpret natural language queries and map them to relevant file metadata and content. This semantic search can also operate on the filtered candidate set.

Users can first perform a basic search by specifying filters (such as directory, extension, date, and file size), then refine the results using similarity search techniques. By centralizing metadata in the SQLite database, the tool remains simple to install and maintain while scaling to millions of entries.

---

## **Roadmap**

1. **Data Acquisition & Metadata Extraction**
   - **File Scanning:**  
     Traverse the file system to read all files and directories.  
     *Note:* The separate tree structure cache is no longer needed because all hierarchy details will be stored in the database.
   - **Metadata Population:**  
     For each file/directory, extract and compute:
     - Absolute path (and optionally a dedicated directory field)
     - File attributes (extension, creation/modification dates, file size, type)
     - Unique identifier (int64 ID)
   - **Database Storage:**  
     Insert these metadata records into an SQLite database. Ensure proper indexing (on the absolute path, directory, dates, etc.) for fast query performance.

2. **Vector Embedding & FAISS Indexing**
   - **Embedding Generation:**  
     Compute embeddings (for file titles, content summaries, etc.) using your chosen model.
   - **FAISS Index Construction:**  
     Create a FAISS index (wrapped with `IndexIDMap`) to store each embedding along with its unique ID from the metadata database.
   - **Storage & Synchronization:**  
     The FAISS index and SQLite database remain synchronized by using the unique ID as the common key.

3. **Multi-Stage Query Pipeline**
   
   **Stage 1: Basic Metadata Filtering**
   - **User Input:**  
     Accept filters from the user (e.g., search within a specific directory, by file extension, date range, file size).
   - **SQLite Query:**  
     Run SQL queries on the metadata database to retrieve the candidate file IDs that match the criteria.
   - **Output:**  
     Obtain a subset of file IDs that represent the filtered set of files.

   **Stage 2: Semantic Similarity Search**
   - **Approach Options:**
     - **Re-indexing Candidate Embeddings:**  
       Retrieve embeddings for the candidate IDs and build a temporary FAISS index to run a similarity search on a limited set.
     - **Post-Filtering Full Index Results:**  
       Run the similarity search on the full FAISS index and then filter the results by intersecting with the candidate IDs.
   - **User-Extended Search:**  
     Allow the user to refine the initial metadata-based results with a semantic query—either via vector similarity or LLM-based search—ensuring that the search operates only on the filtered subset.

4. **LLM Integration**
   - **Natural Language Search:**  
     Integrate the existing LLM-based search capability. Construct prompts using the candidate file summaries or names from the metadata database.
   - **Filtered LLM Search:**  
     Ensure that the LLM search uses the same candidate set from the metadata filtering stage to return contextually relevant results.

5. **User Interface (Console/CLI)**
   - **Input & Interaction:**  
     Develop a simple console UI that:
     - Prompts the user for filtering criteria (directory, extensions, dates, sizes).
     - Displays results from the basic metadata query.
     - Accepts a follow-up semantic query for further refinement.
   - **Output:**  
     Show the final list of file paths (and relevant details) corresponding to the matching files.

6. **Testing, Optimization, and Documentation**
   - **Testing:**  
     Write unit and integration tests to validate metadata extraction, database queries, FAISS similarity search, and LLM prompt generation.
   - **Performance Benchmarking:**  
     Compare the performance of re-indexing the candidate set versus post-filtering the full FAISS search results. Tune the SQLite queries and FAISS parameters based on empirical tests.
   - **Documentation:**  
     Update the project README and user guides to detail installation (using SQLite and FAISS, both of which require no separate servers), configuration options, and usage instructions.

7. **Final Integration and Deployment**
   - **Configuration:**  
     Provide a configuration file that allows users to customize filtering options, database paths, and index settings.
   - **Packaging:**  
     Package the project as a standalone Python application or module that can be easily installed via pip.
   - **Deployment:**  
     Ensure that the final product integrates all components seamlessly and provides clear usage instructions.

---

# **Final Project Vision**

*LFind* will be a single, self-contained file search tool that combines the speed of vector similarity search (via FAISS) with the precision of metadata filtering (via SQLite). Users will be able to:
- **Filter files:** Quickly narrow down their search using criteria such as directory, file extension, date, and size.
- **Refine results:** Perform semantic similarity searches on the filtered candidate set—either through vector similarity or LLM-based methods.
- **Seamless Integration:** Enjoy a simple installation process with no need for external servers (thanks to SQLite) and benefit from fast, efficient queries even on large file repositories.
- **User-Friendly Interface:** Interact with the tool via a straightforward console UI that guides them through both basic and advanced search options.
