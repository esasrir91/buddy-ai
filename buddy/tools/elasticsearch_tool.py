import json
from typing import Any, Dict, List, Optional, Union
from os import getenv

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    from elasticsearch import Elasticsearch, helpers
except ImportError:
    raise ImportError("`elasticsearch` not installed. Please install using `pip install elasticsearch`")


class ElasticsearchTools(Toolkit):
    def __init__(
        self,
        hosts: Optional[List[str]] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        cloud_id: Optional[str] = None,
        use_ssl: bool = True,
        verify_certs: bool = True,
        timeout: int = 30,
        max_retries: int = 3,
        # Tool enabling flags
        create_index: bool = True,
        delete_index: bool = True,
        list_indices: bool = True,
        index_document: bool = True,
        get_document: bool = True,
        update_document: bool = True,
        delete_document: bool = True,
        search_documents: bool = True,
        bulk_operations: bool = True,
        get_mapping: bool = True,
        put_mapping: bool = True,
        create_alias: bool = True,
        get_cluster_health: bool = True,
        get_index_stats: bool = True,
        reindex_data: bool = True,
        analyze_text: bool = True,
        create_template: bool = True,
        **kwargs,
    ):
        """Initialize Elasticsearch Tools.

        Args:
            hosts (Optional[List[str]]): List of Elasticsearch hosts
            username (Optional[str]): Username for authentication
            password (Optional[str]): Password for authentication
            api_key (Optional[str]): API key for authentication
            cloud_id (Optional[str]): Elastic Cloud ID
            use_ssl (bool): Whether to use SSL
            verify_certs (bool): Whether to verify SSL certificates
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retries
        """
        # Get connection parameters
        self.hosts = hosts or [getenv("ELASTICSEARCH_HOST", "localhost:9200")]
        self.username = username or getenv("ELASTICSEARCH_USERNAME")
        self.password = password or getenv("ELASTICSEARCH_PASSWORD")
        self.api_key = api_key or getenv("ELASTICSEARCH_API_KEY")
        self.cloud_id = cloud_id or getenv("ELASTICSEARCH_CLOUD_ID")

        # Build Elasticsearch client configuration
        es_config = {
            "hosts": self.hosts,
            "timeout": timeout,
            "max_retries": max_retries,
            "retry_on_timeout": True,
        }

        # Add authentication
        if self.api_key:
            es_config["api_key"] = self.api_key
        elif self.username and self.password:
            es_config["basic_auth"] = (self.username, self.password)

        # Add cloud configuration
        if self.cloud_id:
            es_config["cloud_id"] = self.cloud_id

        # SSL configuration
        if use_ssl:
            es_config["scheme"] = "https"
            es_config["verify_certs"] = verify_certs

        # Initialize Elasticsearch client
        try:
            self.es_client = Elasticsearch(**es_config)
            # Test connection
            if not self.es_client.ping():
                logger.warning("Could not connect to Elasticsearch")
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch client: {e}")
            raise

        # Build tools list based on enabled features
        tools: List[Any] = []
        if create_index:
            tools.append(self.create_index)
        if delete_index:
            tools.append(self.delete_index)
        if list_indices:
            tools.append(self.list_indices)
        if index_document:
            tools.append(self.index_document)
        if get_document:
            tools.append(self.get_document)
        if update_document:
            tools.append(self.update_document)
        if delete_document:
            tools.append(self.delete_document)
        if search_documents:
            tools.append(self.search_documents)
        if bulk_operations:
            tools.append(self.bulk_operations)
        if get_mapping:
            tools.append(self.get_mapping)
        if put_mapping:
            tools.append(self.put_mapping)
        if create_alias:
            tools.append(self.create_alias)
        if get_cluster_health:
            tools.append(self.get_cluster_health)
        if get_index_stats:
            tools.append(self.get_index_stats)
        if reindex_data:
            tools.append(self.reindex_data)
        if analyze_text:
            tools.append(self.analyze_text)
        if create_template:
            tools.append(self.create_template)

        super().__init__(name="elasticsearch", tools=tools, **kwargs)

    def create_index(self, index_name: str, mappings: Optional[Dict] = None, settings: Optional[Dict] = None) -> str:
        """Create a new Elasticsearch index.

        Args:
            index_name (str): Name of the index to create
            mappings (Optional[Dict]): Index mappings definition
            settings (Optional[Dict]): Index settings

        Returns:
            str: Success or error message
        """
        try:
            log_debug(f"Creating index: {index_name}")

            body = {}
            if mappings:
                body["mappings"] = mappings
            if settings:
                body["settings"] = settings

            result = self.es_client.indices.create(index=index_name, body=body if body else None)
            return json.dumps({
                "success": f"Index '{index_name}' created successfully",
                "acknowledged": result.get("acknowledged", False),
                "shards_acknowledged": result.get("shards_acknowledged", False)
            })

        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return json.dumps({"error": f"Failed to create index: {str(e)}"})

    def delete_index(self, index_name: str) -> str:
        """Delete an Elasticsearch index.

        Args:
            index_name (str): Name of the index to delete

        Returns:
            str: Success or error message
        """
        try:
            log_debug(f"Deleting index: {index_name}")

            result = self.es_client.indices.delete(index=index_name)
            return json.dumps({
                "success": f"Index '{index_name}' deleted successfully",
                "acknowledged": result.get("acknowledged", False)
            })

        except Exception as e:
            logger.error(f"Error deleting index: {e}")
            return json.dumps({"error": f"Failed to delete index: {str(e)}"})

    def list_indices(self, pattern: Optional[str] = None) -> str:
        """List all indices in the Elasticsearch cluster.

        Args:
            pattern (Optional[str]): Pattern to filter indices

        Returns:
            str: JSON list of indices
        """
        try:
            log_debug(f"Listing indices with pattern: {pattern}")

            if pattern:
                indices = self.es_client.cat.indices(index=pattern, format="json")
            else:
                indices = self.es_client.cat.indices(format="json")

            return json.dumps({
                "indices": indices,
                "total_count": len(indices)
            })

        except Exception as e:
            logger.error(f"Error listing indices: {e}")
            return json.dumps({"error": f"Failed to list indices: {str(e)}"})

    def index_document(self, index_name: str, document: Dict, doc_id: Optional[str] = None) -> str:
        """Index a document into Elasticsearch.

        Args:
            index_name (str): Name of the index
            document (Dict): Document to index
            doc_id (Optional[str]): Document ID (auto-generated if None)

        Returns:
            str: Index result
        """
        try:
            log_debug(f"Indexing document in index: {index_name}")

            if doc_id:
                result = self.es_client.index(index=index_name, id=doc_id, body=document)
            else:
                result = self.es_client.index(index=index_name, body=document)

            return json.dumps({
                "success": f"Document indexed successfully",
                "index": result["_index"],
                "id": result["_id"],
                "version": result["_version"],
                "result": result["result"]
            })

        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            return json.dumps({"error": f"Failed to index document: {str(e)}"})

    def get_document(self, index_name: str, doc_id: str) -> str:
        """Retrieve a document from Elasticsearch.

        Args:
            index_name (str): Name of the index
            doc_id (str): Document ID

        Returns:
            str: Document data or error message
        """
        try:
            log_debug(f"Getting document {doc_id} from index: {index_name}")

            result = self.es_client.get(index=index_name, id=doc_id)
            return json.dumps({
                "found": result["found"],
                "source": result.get("_source", {}),
                "index": result["_index"],
                "id": result["_id"],
                "version": result.get("_version")
            })

        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return json.dumps({"error": f"Failed to get document: {str(e)}"})

    def update_document(self, index_name: str, doc_id: str, update_body: Dict) -> str:
        """Update a document in Elasticsearch.

        Args:
            index_name (str): Name of the index
            doc_id (str): Document ID
            update_body (Dict): Update body (should contain 'doc' or 'script')

        Returns:
            str: Update result
        """
        try:
            log_debug(f"Updating document {doc_id} in index: {index_name}")

            result = self.es_client.update(index=index_name, id=doc_id, body=update_body)
            return json.dumps({
                "success": f"Document updated successfully",
                "index": result["_index"],
                "id": result["_id"],
                "version": result["_version"],
                "result": result["result"]
            })

        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return json.dumps({"error": f"Failed to update document: {str(e)}"})

    def delete_document(self, index_name: str, doc_id: str) -> str:
        """Delete a document from Elasticsearch.

        Args:
            index_name (str): Name of the index
            doc_id (str): Document ID

        Returns:
            str: Delete result
        """
        try:
            log_debug(f"Deleting document {doc_id} from index: {index_name}")

            result = self.es_client.delete(index=index_name, id=doc_id)
            return json.dumps({
                "success": f"Document deleted successfully",
                "index": result["_index"],
                "id": result["_id"],
                "version": result["_version"],
                "result": result["result"]
            })

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return json.dumps({"error": f"Failed to delete document: {str(e)}"})

    def search_documents(self, index_name: str, query: Dict, size: int = 10, from_: int = 0) -> str:
        """Search for documents in Elasticsearch.

        Args:
            index_name (str): Name of the index to search
            query (Dict): Elasticsearch query DSL
            size (int): Number of results to return
            from_ (int): Offset for pagination

        Returns:
            str: Search results
        """
        try:
            log_debug(f"Searching in index: {index_name}")

            result = self.es_client.search(
                index=index_name,
                body={"query": query},
                size=size,
                from_=from_
            )

            hits = result["hits"]
            return json.dumps({
                "total_hits": hits["total"]["value"],
                "max_score": hits.get("max_score"),
                "documents": [
                    {
                        "id": hit["_id"],
                        "score": hit["_score"],
                        "source": hit["_source"]
                    }
                    for hit in hits["hits"]
                ],
                "took": result["took"]
            })

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return json.dumps({"error": f"Failed to search documents: {str(e)}"})

    def bulk_operations(self, operations: List[Dict]) -> str:
        """Perform bulk operations in Elasticsearch.

        Args:
            operations (List[Dict]): List of bulk operations

        Returns:
            str: Bulk operation results
        """
        try:
            log_debug(f"Performing bulk operations: {len(operations)} operations")

            result = helpers.bulk(self.es_client, operations)
            return json.dumps({
                "success": f"Bulk operations completed",
                "successful": result[0],
                "failed": result[1] if len(result) > 1 else []
            })

        except Exception as e:
            logger.error(f"Error performing bulk operations: {e}")
            return json.dumps({"error": f"Failed to perform bulk operations: {str(e)}"})

    def get_mapping(self, index_name: str) -> str:
        """Get the mapping for an index.

        Args:
            index_name (str): Name of the index

        Returns:
            str: Index mapping
        """
        try:
            log_debug(f"Getting mapping for index: {index_name}")

            result = self.es_client.indices.get_mapping(index=index_name)
            return json.dumps(result)

        except Exception as e:
            logger.error(f"Error getting mapping: {e}")
            return json.dumps({"error": f"Failed to get mapping: {str(e)}"})

    def put_mapping(self, index_name: str, mapping: Dict) -> str:
        """Update the mapping for an index.

        Args:
            index_name (str): Name of the index
            mapping (Dict): New mapping definition

        Returns:
            str: Success or error message
        """
        try:
            log_debug(f"Updating mapping for index: {index_name}")

            result = self.es_client.indices.put_mapping(index=index_name, body=mapping)
            return json.dumps({
                "success": f"Mapping updated successfully",
                "acknowledged": result.get("acknowledged", False)
            })

        except Exception as e:
            logger.error(f"Error updating mapping: {e}")
            return json.dumps({"error": f"Failed to update mapping: {str(e)}"})

    def create_alias(self, alias_name: str, index_name: str, filter_query: Optional[Dict] = None) -> str:
        """Create an alias for an index.

        Args:
            alias_name (str): Name of the alias
            index_name (str): Name of the index
            filter_query (Optional[Dict]): Optional filter for the alias

        Returns:
            str: Success or error message
        """
        try:
            log_debug(f"Creating alias {alias_name} for index: {index_name}")

            body = {"actions": [{"add": {"index": index_name, "alias": alias_name}}]}
            
            if filter_query:
                body["actions"][0]["add"]["filter"] = filter_query

            result = self.es_client.indices.update_aliases(body=body)
            return json.dumps({
                "success": f"Alias '{alias_name}' created successfully",
                "acknowledged": result.get("acknowledged", False)
            })

        except Exception as e:
            logger.error(f"Error creating alias: {e}")
            return json.dumps({"error": f"Failed to create alias: {str(e)}"})

    def get_cluster_health(self) -> str:
        """Get cluster health information.

        Returns:
            str: Cluster health data
        """
        try:
            log_debug("Getting cluster health")

            result = self.es_client.cluster.health()
            return json.dumps(result)

        except Exception as e:
            logger.error(f"Error getting cluster health: {e}")
            return json.dumps({"error": f"Failed to get cluster health: {str(e)}"})

    def get_index_stats(self, index_name: Optional[str] = None) -> str:
        """Get statistics for indices.

        Args:
            index_name (Optional[str]): Specific index name, or all indices if None

        Returns:
            str: Index statistics
        """
        try:
            log_debug(f"Getting stats for index: {index_name or 'all indices'}")

            if index_name:
                result = self.es_client.indices.stats(index=index_name)
            else:
                result = self.es_client.indices.stats()

            return json.dumps(result)

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return json.dumps({"error": f"Failed to get index stats: {str(e)}"})

    def reindex_data(self, source_index: str, dest_index: str, query: Optional[Dict] = None) -> str:
        """Reindex data from one index to another.

        Args:
            source_index (str): Source index name
            dest_index (str): Destination index name
            query (Optional[Dict]): Optional query to filter documents

        Returns:
            str: Reindex result
        """
        try:
            log_debug(f"Reindexing from {source_index} to {dest_index}")

            body = {
                "source": {"index": source_index},
                "dest": {"index": dest_index}
            }

            if query:
                body["source"]["query"] = query

            result = self.es_client.reindex(body=body, wait_for_completion=True)
            return json.dumps({
                "success": f"Reindexing completed",
                "total": result.get("total", 0),
                "created": result.get("created", 0),
                "updated": result.get("updated", 0),
                "deleted": result.get("deleted", 0),
                "took": result.get("took", 0)
            })

        except Exception as e:
            logger.error(f"Error reindexing data: {e}")
            return json.dumps({"error": f"Failed to reindex data: {str(e)}"})

    def analyze_text(self, text: str, analyzer: str = "standard", index_name: Optional[str] = None) -> str:
        """Analyze text using Elasticsearch analyzers.

        Args:
            text (str): Text to analyze
            analyzer (str): Analyzer to use
            index_name (Optional[str]): Index to use for analysis (for custom analyzers)

        Returns:
            str: Analysis result
        """
        try:
            log_debug(f"Analyzing text with analyzer: {analyzer}")

            body = {"text": text, "analyzer": analyzer}
            
            if index_name:
                result = self.es_client.indices.analyze(index=index_name, body=body)
            else:
                result = self.es_client.indices.analyze(body=body)

            return json.dumps({
                "tokens": [
                    {
                        "token": token["token"],
                        "start_offset": token["start_offset"],
                        "end_offset": token["end_offset"],
                        "type": token["type"],
                        "position": token["position"]
                    }
                    for token in result["tokens"]
                ]
            })

        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return json.dumps({"error": f"Failed to analyze text: {str(e)}"})

    def create_template(self, template_name: str, index_patterns: List[str], mappings: Dict, settings: Optional[Dict] = None) -> str:
        """Create an index template.

        Args:
            template_name (str): Name of the template
            index_patterns (List[str]): Index patterns that this template applies to
            mappings (Dict): Mappings definition
            settings (Optional[Dict]): Index settings

        Returns:
            str: Success or error message
        """
        try:
            log_debug(f"Creating template: {template_name}")

            body = {
                "index_patterns": index_patterns,
                "mappings": mappings
            }

            if settings:
                body["settings"] = settings

            result = self.es_client.indices.put_template(name=template_name, body=body)
            return json.dumps({
                "success": f"Template '{template_name}' created successfully",
                "acknowledged": result.get("acknowledged", False)
            })

        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return json.dumps({"error": f"Failed to create template: {str(e)}"})