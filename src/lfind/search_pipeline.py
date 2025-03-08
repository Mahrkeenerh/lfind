from typing import List, Dict, Any, Optional, Set, Tuple
import os

from .db_manager import DatabaseManager
from .embed_manager import EmbedManager
from .embedding.service import EmbeddingService
from .llm_service import LLMService

class SearchPipeline:
    """Multi-stage search pipeline with history support."""
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        config: Dict[str, Any]
    ):
        """Initialize the search pipeline.
        
        Args:
            db_manager: Database manager for file metadata
            embedding_service: Service for creating and comparing embeddings
            llm_service: Service for LLM-based search
            config: Application configuration
        """
        self.db = db_manager
        self.embedding = embedding_service
        self.llm = llm_service
        self.config = config
        self.search_history = []
    
    def add_to_history(
        self, 
        query: str, 
        results: List[Dict[str, Any]], 
        search_type: str,
        params: Dict[str, Any]
    ) -> None:
        """Add search results to history.
        
        Args:
            query: The search query
            results: The search results
            search_type: Type of search (extension, semantic, llm)
            params: Additional parameters for the search
        """
        self.search_history.append({
            'query': query,
            'results': results,
            'search_type': search_type,
            'params': params,
            'result_count': len(results)
        })
    
    def filter_by_extension(
        self, 
        extensions: List[str], 
        directory: Optional[str] = None,
        previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Filter files by extension.
        
        Args:
            extensions: List of file extensions to include (e.g. [".py", ".txt"])
            directory: Optional directory to search in
            previous_results: Optional previous search results to filter
            
        Returns:
            List of matching file records
        """
        # Ensure extensions have a leading dot and are lowercase
        normalized_extensions = [
            ext.lower() if ext.startswith(".") else f".{ext.lower()}" 
            for ext in extensions
        ]
        
        if previous_results:
            # Filter the previous results
            filtered_results = []
            for record in previous_results:
                file_name = record.get('name', '')
                _, ext = os.path.splitext(file_name)
                if ext.lower() in normalized_extensions:
                    filtered_results.append(record)
            results = filtered_results
        else:
            # Get fresh results from the database
            results = self.db.get_files_by_criteria(
                extensions=normalized_extensions,
                directory=directory,
                file_type="file"
            )
        
        self.add_to_history(
            query=f"extension:{','.join(extensions)}",
            results=results,
            search_type="extension",
            params={
                'extensions': extensions,
                'directory': directory
            }
        )
        
        return results
    
    def search_semantic(
        self,
        query: str,
        top_k: int = 10,
        directory: Optional[str] = None,
        extensions: Optional[List[str]] = None,
        previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Search files by semantic similarity.
        
        Args:
            query: The search query
            top_k: Number of results to return
            directory: Optional directory to search in
            extensions: Optional list of file extensions to filter
            previous_results: Optional previous search results to filter
            
        Returns:
            List of matching file records
        """
        # Create query embedding
        query_embedding = self.embedding.embed_query(query)
        
        # Choose approach based on the size of the candidate set
        if previous_results and len(previous_results) < 1000:
            # Limited Index Approach: Create a temporary index for the candidate set
            
            # Get file IDs from previous results
            file_ids = [r['id'] for r in previous_results if 'id' in r]
            
            if len(file_ids) == 0:
                return []
            
            # Create temporary index for these files
            temp_manager = EmbedManager(
                dim=self.embedding.embed_manager.dim,
                metric=self.embedding.embed_manager.metric
            )
            
            # Get embeddings for candidate files
            embeddings = []
            matched_ids = []
            
            for file_record in previous_results:
                embedding_id = file_record.get('embedding_id')
                file_id = file_record.get('id')
                
                if embedding_id is not None and file_id is not None:
                    # Get the embedding from the database or embedding service
                    file_path = file_record.get('absolute_path')
                    emb, _ = self.embedding.embed_file(file_path)
                    if emb is not None:
                        embeddings.append(emb)
                        matched_ids.append(file_id)
            
            if not embeddings:
                return []
                
            # Add embeddings to temporary index
            temp_manager.add_embeddings(embeddings)
            
            # Search in temporary index
            distances, indices = temp_manager.search(query_embedding, k=min(top_k, len(embeddings)))
            
            # Map results back to file records
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(matched_ids):
                    file_id = matched_ids[idx]
                    for record in previous_results:
                        if record.get('id') == file_id:
                            results.append(record)
                            break
            
        else:
            # Post-Filtering Approach: Search full index and filter
            # This approach is used when there are no previous results or too many
            
            # Get candidate set through basic filtering if needed
            candidate_results = previous_results
            if not candidate_results:
                candidate_results = self.db.get_files_by_criteria(
                    directory=directory,
                    extensions=extensions,
                    file_type="file"
                )
            
            # Search the full index
            similarity_results = self.embedding.search_similar(query, k=top_k * 10)  # Get more results to filter
            
            # Filter to intersection with candidate set
            candidate_ids = {r['id'] for r in candidate_results if 'id' in r}
            results = []
            
            for idx, score in similarity_results:
                file_record = self.db.get_file_by_id(idx)
                if file_record and file_record.get('id') in candidate_ids:
                    results.append(file_record)
                    
                if len(results) >= top_k:
                    break
        
        # Add to history
        self.add_to_history(
            query=query,
            results=results,
            search_type="semantic",
            params={
                'top_k': top_k,
                'directory': directory,
                'extensions': extensions
            }
        )
        
        return results
    
    def search_llm(
        self,
        query: str,
        directory: Optional[str] = None,
        extensions: Optional[List[str]] = None,
        use_hard_model: bool = False,
        previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Search files using LLM-based natural language matching.
        
        Args:
            query: The natural language search query
            directory: Optional directory to search in
            extensions: Optional list of file extensions to filter
            use_hard_model: Whether to use the more powerful LLM model
            previous_results: Optional previous search results to filter
            
        Returns:
            List of matching file records
        """
        # Get candidate files either from previous results or a new database query
        candidate_records = previous_results
        if not candidate_records:
            candidate_records = self.db.get_files_by_criteria(
                directory=directory,
                extensions=extensions,
                file_type="file"
            )
        
        if not candidate_records:
            return []
        
        # Extract filenames from records for LLM search
        file_names = [record.get('name', '') for record in candidate_records]
        
        # Perform LLM search
        matching_names = self.llm.search_files(query, file_names, use_hard_model)
        
        # Match results to file records
        results = []
        for name in matching_names:
            for record in candidate_records:
                if record.get('name') == name:
                    results.append(record)
                    break
        
        # Add to history
        self.add_to_history(
            query=query,
            results=results,
            search_type="llm",
            params={
                'directory': directory,
                'extensions': extensions,
                'use_hard_model': use_hard_model
            }
        )
        
        return results
    
    def multi_search(
        self,
        query: str,
        directory: Optional[str] = None,
        extensions: Optional[List[str]] = None,
        use_semantic: bool = True,
        use_llm: bool = True,
        use_hard_llm: bool = False,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform multi-stage search using all available methods.
        
        Args:
            query: The search query
            directory: Optional directory to search in
            extensions: Optional list of file extensions to filter
            use_semantic: Whether to use semantic search
            use_llm: Whether to use LLM search
            use_hard_llm: Whether to use the more powerful LLM model
            top_k: Number of results to return
            
        Returns:
            List of matching file records
        """
        # Stage 1: Basic metadata filtering
        base_results = self.db.get_files_by_criteria(
            directory=directory,
            extensions=extensions,
            file_type="file"
        )
        
        if not base_results:
            return []
        
        results = []
        
        # Stage 2: Semantic search if requested
        if use_semantic:
            semantic_results = self.search_semantic(
                query=query,
                top_k=top_k,
                previous_results=base_results
            )
            results.extend(semantic_results)
        
        # Stage 3: LLM search if requested
        if use_llm:
            llm_results = self.search_llm(
                query=query,
                use_hard_model=use_hard_llm,
                previous_results=base_results
            )
            
            # Add LLM results that weren't already found in semantic search
            result_ids = {r['id'] for r in results if 'id' in r}
            for record in llm_results:
                if record.get('id') not in result_ids:
                    results.append(record)
                    result_ids.add(record.get('id'))
                    
                    # Limit to top_k results
                    if len(results) >= top_k:
                        break
        
        # If neither semantic nor LLM search was used, return metadata results directly
        if not use_semantic and not use_llm:
            results = base_results[:top_k]
        
        # Add combined search to history
        self.add_to_history(
            query=query,
            results=results,
            search_type="multi",
            params={
                'directory': directory,
                'extensions': extensions,
                'use_semantic': use_semantic,
                'use_llm': use_llm,
                'use_hard_llm': use_hard_llm,
                'top_k': top_k
            }
        )
        
        return results[:top_k]
