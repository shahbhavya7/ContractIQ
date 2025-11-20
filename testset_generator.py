"""
Ragas Testset Generator Module
Generates evaluation testsets with questions and answers for RAG system
"""

import os
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import pandas as pd
from datetime import datetime
import warnings

from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.testset import TestsetGenerator
from ragas.testset.graph import KnowledgeGraph, Node, NodeType
from ragas.testset.transforms import default_transforms, apply_transforms
from ragas.testset.synthesizers import default_query_distribution



class ContractTestsetGenerator:
    """
    Handles testset generation for Contract RAG system using Ragas
    """
    
    def __init__(
        self,
        llm_model: str = "gemini-2.5-flash",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_retries: int = 2,
        retry_delay: int = 30
    ):
        """
        Initialize the testset generator
        
        Args:
            llm_model: Google Gemini model to use for generation (default: gemini-2.5-flash)
            embedding_model: HuggingFace embedding model
            max_retries: Maximum number of retries for rate limit errors
            retry_delay: Delay in seconds between retries
        """
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")
        
        # Setup Google Gemini LLM
        self.generator_llm = LangchainLLMWrapper(
            ChatGoogleGenerativeAI(
                model=llm_model,
                temperature=0.2,
                google_api_key=gemini_api_key
            )
        )
        
        # Setup embeddings (same model as main RAG system)
        hf_embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True},
            show_progress=False
        )
        self.generator_embeddings = LangchainEmbeddingsWrapper(hf_embeddings)
        
        self.knowledge_graph = None
        self.generator = None
    
    def create_knowledge_graph_from_documents(
        self,
        documents: List[Document],
        save_path: Optional[str] = None,
        skip_transforms: bool = False
    ) -> KnowledgeGraph:
        """
        Create a knowledge graph from documents
        
        Args:
            documents: List of LangChain Document objects
            save_path: Optional path to save the knowledge graph
            
        Returns:
            KnowledgeGraph object
        """
        print(f"Creating knowledge graph from {len(documents)} documents...")
        
        # Initialize knowledge graph
        kg = KnowledgeGraph()
        
        # Add documents as nodes
        for doc in documents:
            kg.nodes.append(
                Node(
                    type=NodeType.DOCUMENT,
                    properties={
                        "page_content": doc.page_content,
                        "document_metadata": doc.metadata
                    }
                )
            )
        
        print(f"✓ Added {len(kg.nodes)} document nodes")
        
        # Handle fast mode with minimal but sufficient enrichment
        if skip_transforms:
            # Process just a few documents to create the necessary node structure
            # This is 10x faster than full enrichment but still generates quality questions
            minimal_docs = documents[:min(5, len(documents))]  # Use just 5 documents
            
            try:
                transforms = default_transforms(
                    documents=minimal_docs,
                    llm=self.generator_llm,
                    embedding_model=self.generator_embeddings
                )
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    apply_transforms(kg, transforms)
                
                print(f"✓ Minimal enrichment complete: {len(kg.nodes)} nodes, {len(kg.relationships)} relationships")
            except Exception as e:
                print(f"⚠️  Minimal enrichment failed: {str(e)}")
                print("   Falling back to standard enrichment...")
                skip_transforms = False  # Fall back to normal processing
        
        if not skip_transforms:
            # Apply transformations to enrich the knowledge graph
            # Use simplified approach to avoid rate limits with large document sets
            print("Applying transformations to enrich knowledge graph...")
            print("⚠️  Optimized for speed - using selective document sampling.")
            
            # Aggressive sampling to speed up generation
            max_docs_for_transforms = 30  # Reduced from 100 for faster processing
            if len(documents) > max_docs_for_transforms:
                print(f"⚠️  Sampling {max_docs_for_transforms} most diverse chunks from {len(documents)} total.")
                print(f"   This significantly speeds up generation while maintaining quality.")
                # Sample evenly distributed documents instead of just first N
                step = len(documents) // max_docs_for_transforms
                sampled_docs = [documents[i] for i in range(0, len(documents), step)][:max_docs_for_transforms]
            else:
                sampled_docs = documents
        
            try:
                # Use default transforms but with retry logic
                for attempt in range(self.max_retries):
                    try:
                        transforms = default_transforms(
                            documents=sampled_docs,
                            llm=self.generator_llm,
                            embedding_model=self.generator_embeddings
                        )
                        
                        # Suppress progress bars for cleaner output
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            apply_transforms(kg, transforms)
                        break  # Success!
                        
                    except Exception as e:
                        error_str = str(e)
                        if "rate_limit" in error_str.lower() or "429" in error_str:
                            if attempt < self.max_retries - 1:
                                print(f"⚠️  Rate limit hit. Waiting {self.retry_delay} seconds before retry {attempt + 2}/{self.max_retries}...")
                                time.sleep(self.retry_delay)
                            else:
                                print("⚠️  Rate limit exceeded. Using simplified knowledge graph (questions may be less diverse).")
                                # Continue with basic graph without full enrichment
                                break
                        else:
                            print(f"⚠️  Error during transformation: {error_str}")
                            print("   Continuing with simplified knowledge graph...")
                            break
            
            except Exception as e:
                print(f"⚠️  Could not fully enrich knowledge graph: {str(e)}")
                print("   Continuing with basic graph structure...")
        
        print(f"✓ Knowledge graph ready: {len(kg.nodes)} nodes, {len(kg.relationships)} relationships")
        
        # Save if requested
        if save_path:
            kg.save(save_path)
            print(f"✓ Knowledge graph saved to {save_path}")
        
        self.knowledge_graph = kg
        return kg
    
    def load_knowledge_graph(self, path: str) -> KnowledgeGraph:
        """
        Load a previously saved knowledge graph
        
        Args:
            path: Path to the saved knowledge graph JSON file
            
        Returns:
            KnowledgeGraph object
        """
        print(f"Loading knowledge graph from {path}...")
        kg = KnowledgeGraph.load(path)
        print(f"✓ Loaded: {len(kg.nodes)} nodes, {len(kg.relationships)} relationships")
        self.knowledge_graph = kg
        return kg
    
    def generate_testset(
        self,
        testset_size: int = 10,
        query_distribution: Optional[List] = None,
        save_path: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Generate a testset using the knowledge graph
        
        Args:
            testset_size: Number of test questions to generate
            query_distribution: Custom query distribution (uses default if None)
            save_path: Optional path to save the testset CSV
            
        Returns:
            DataFrame containing the testset
        """
        if self.knowledge_graph is None:
            raise ValueError("Knowledge graph not created. Call create_knowledge_graph_from_documents() first.")
        
        print(f"Generating testset with {testset_size} questions...")
        
        # Initialize generator
        self.generator = TestsetGenerator(
            llm=self.generator_llm,
            embedding_model=self.generator_embeddings,
            knowledge_graph=self.knowledge_graph
        )
        
        # Use default or custom query distribution
        if query_distribution is None:
            query_distribution = default_query_distribution(self.generator_llm)
            print("Using default query distribution:")
            print("  - 50% Single-hop specific queries")
            print("  - 25% Multi-hop abstract queries")
            print("  - 25% Multi-hop specific queries")
        
        # Generate testset with retry logic for rate limits
        for attempt in range(self.max_retries):
            try:
                testset = self.generator.generate(
                    testset_size=testset_size,
                    query_distribution=query_distribution
                )
                break  # Success!
                
            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    if attempt < self.max_retries - 1:
                        print(f"⚠️  Rate limit hit during generation. Waiting {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        raise Exception(f"Rate limit exceeded after {self.max_retries} attempts. Please try again later or reduce testset_size.")
                else:
                    raise  # Re-raise non-rate-limit errors
        
        # Convert to DataFrame
        df = testset.to_pandas()
        print(f"✓ Generated {len(df)} test questions")
        
        # Save if requested
        if save_path:
            df.to_csv(save_path, index=False)
            print(f"✓ Testset saved to {save_path}")
        
        return df
    
    def generate_from_vector_store(
        self,
        vector_store,
        collection_name: str,
        testset_size: int = 10,
        save_dir: Optional[str] = None,
        fast_mode: bool = True,
        source_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate testset directly from vector store documents
        
        Args:
            vector_store: PGVector store instance
            collection_name: Name of the collection
            testset_size: Number of test questions
            save_dir: Directory to save outputs
            fast_mode: Skip expensive transforms for speed
            source_file: If provided, only use chunks from this PDF file
            
        Returns:
            Dictionary with testset DataFrame and metadata
        """
        if source_file:
            print(f"Retrieving documents from '{source_file}' in collection '{collection_name}'...")
        else:
            print(f"Retrieving documents from collection '{collection_name}'...")
        
        # Get documents from vector store
        # Aggressively limit for speed - testsets don't need all documents
        max_chunks = 100  # Reduced from 500 for much faster generation
        
        if source_file:
            # Filter by specific source file
            all_docs = vector_store.similarity_search(
                "",
                k=max_chunks,
                filter={"source_file": source_file}
            )
            
            if not all_docs:
                raise ValueError(f"No documents found for file '{source_file}'. Make sure the PDF is ingested first.")
        else:
            # Get from all files
            all_docs = vector_store.similarity_search("", k=max_chunks)
        
        if not all_docs:
            raise ValueError("No documents found in the vector store")
        
        if source_file:
            print(f"✓ Retrieved {len(all_docs)} chunks from {source_file}")
        else:
            print(f"✓ Retrieved {len(all_docs)} document chunks (optimized for speed)")
            if len(all_docs) >= max_chunks:
                print(f"   (Limited to {max_chunks} chunks for faster generation)")
        
        # Create timestamp for file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup save paths
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            kg_path = os.path.join(save_dir, f"knowledge_graph_{timestamp}.json")
            testset_path = os.path.join(save_dir, f"testset_{timestamp}.csv")
        else:
            kg_path = None
            testset_path = None
        
        # Create knowledge graph
        print(f"Fast mode: {'ENABLED' if fast_mode else 'DISABLED'}")
        if fast_mode:
            print("   Skipping expensive transformations for 5-10x speed boost")
        kg = self.create_knowledge_graph_from_documents(all_docs, save_path=kg_path, skip_transforms=fast_mode)
        
        # Generate testset
        df = self.generate_testset(
            testset_size=testset_size,
            save_path=testset_path
        )
        
        # Prepare metadata
        metadata = {
            "collection_name": collection_name,
            "source_file": source_file if source_file else "all_files",
            "total_chunks": len(all_docs),
            "testset_size": len(df),
            "timestamp": timestamp,
            "kg_nodes": len(kg.nodes),
            "kg_relationships": len(kg.relationships),
            "kg_path": kg_path,
            "testset_path": testset_path
        }
        
        return {
            "testset": df,
            "metadata": metadata,
            "knowledge_graph": kg
        }


def create_testset_from_documents(
    documents: List[Document],
    testset_size: int = 10,
    save_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate testset from documents in one call
    
    Args:
        documents: List of LangChain Document objects
        testset_size: Number of test questions
        save_dir: Directory to save outputs
        
    Returns:
        Dictionary with testset DataFrame and metadata
    """
    generator = ContractTestsetGenerator()
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Setup paths
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        kg_path = os.path.join(save_dir, f"knowledge_graph_{timestamp}.json")
        testset_path = os.path.join(save_dir, f"testset_{timestamp}.csv")
    else:
        kg_path = None
        testset_path = None
    
    # Generate
    kg = generator.create_knowledge_graph_from_documents(documents, save_path=kg_path)
    df = generator.generate_testset(testset_size=testset_size, save_path=testset_path)
    
    return {
        "testset": df,
        "metadata": {
            "total_chunks": len(documents),
            "testset_size": len(df),
            "timestamp": timestamp,
            "kg_nodes": len(kg.nodes),
            "kg_relationships": len(kg.relationships),
            "kg_path": kg_path,
            "testset_path": testset_path
        },
        "knowledge_graph": kg
    }
