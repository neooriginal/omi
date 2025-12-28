"""
Integration tests for knowledge graph cleanup when memories are deleted.

These tests verify that the knowledge graph correctly updates when memories are deleted,
ensuring no orphaned references remain.

Setup:
1. pip install pytest
2. Set GOOGLE_APPLICATION_CREDENTIALS or authenticate with gcloud
3. Run: pytest backend/tests/integration/test_knowledge_graph_memory_deletion.py -v
"""

import pytest
import os
import uuid
from datetime import datetime, timezone

import database.memories as memories_db
import database.knowledge_graph as kg_db


@pytest.fixture
def test_user_id():
    """Get or create a test user ID"""
    user_id = os.getenv('TEST_USER_ID', f'test-user-{uuid.uuid4()}')
    return user_id


@pytest.fixture
def cleanup_test_data(test_user_id):
    """Cleanup test data after tests"""
    yield
    # Cleanup: Delete all test memories and knowledge graph
    try:
        memories_db.delete_all_memories(test_user_id)
        kg_db.delete_knowledge_graph(test_user_id)
    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")


class TestKnowledgeGraphMemoryDeletion:
    """Test knowledge graph cleanup when memories are deleted"""

    def test_single_memory_deletion_removes_from_nodes(self, test_user_id, cleanup_test_data):
        """Test that deleting a memory removes its ID from node memory_ids arrays"""
        print(f"\n🧪 Testing node cleanup for user: {test_user_id}")
        
        # Create a test memory
        memory_id = str(uuid.uuid4())
        memory_data = {
            'id': memory_id,
            'content': 'Test memory about Paris',
            'created_at': datetime.now(timezone.utc),
            'user_review': True,
            'scoring': 1.0,
            'category': 'interesting',
            'visibility': 'private'
        }
        memories_db.create_memory(test_user_id, memory_data)
        print(f"Created memory: {memory_id}")
        
        # Create a knowledge node linked to this memory
        node_id = str(uuid.uuid4())
        node_data = {
            'id': node_id,
            'label': 'Paris',
            'node_type': 'place',
            'aliases': [],
            'memory_ids': [memory_id]
        }
        kg_db.upsert_knowledge_node(test_user_id, node_data)
        print(f"Created node: {node_id} with memory_ids: {node_data['memory_ids']}")
        
        # Verify node was created with the memory_id
        node = kg_db.get_knowledge_node(test_user_id, node_id)
        assert node is not None
        assert memory_id in node['memory_ids']
        print(f"✅ Node contains memory_id before deletion")
        
        # Delete the memory
        memories_db.delete_memory(test_user_id, memory_id)
        print(f"Deleted memory: {memory_id}")
        
        # Verify node was deleted (orphaned)
        node = kg_db.get_knowledge_node(test_user_id, node_id)
        assert node is None
        print(f"✅ Orphaned node was deleted")

    def test_single_memory_deletion_removes_from_edges(self, test_user_id, cleanup_test_data):
        """Test that deleting a memory removes its ID from edge memory_ids arrays"""
        print(f"\n🧪 Testing edge cleanup for user: {test_user_id}")
        
        # Create a test memory
        memory_id = str(uuid.uuid4())
        memory_data = {
            'id': memory_id,
            'content': 'John lives in Paris',
            'created_at': datetime.now(timezone.utc),
            'user_review': True,
            'scoring': 1.0,
            'category': 'interesting',
            'visibility': 'private'
        }
        memories_db.create_memory(test_user_id, memory_data)
        
        # Create nodes
        node1_id = str(uuid.uuid4())
        node1_data = {
            'id': node1_id,
            'label': 'John',
            'node_type': 'person',
            'aliases': [],
            'memory_ids': [memory_id]
        }
        kg_db.upsert_knowledge_node(test_user_id, node1_data)
        
        node2_id = str(uuid.uuid4())
        node2_data = {
            'id': node2_id,
            'label': 'Paris',
            'node_type': 'place',
            'aliases': [],
            'memory_ids': [memory_id]
        }
        kg_db.upsert_knowledge_node(test_user_id, node2_data)
        
        # Create an edge linking the nodes
        edge_data = {
            'source_id': node1_id,
            'target_id': node2_id,
            'label': 'lives in',
            'memory_ids': [memory_id]
        }
        kg_db.upsert_knowledge_edge(test_user_id, edge_data)
        edge_id = f"{node1_id}_lives in_{node2_id}"
        print(f"Created edge: {edge_id}")
        
        # Verify edge exists with the memory_id
        edges = kg_db.get_knowledge_edges(test_user_id)
        edge = next((e for e in edges if e['id'] == edge_id), None)
        assert edge is not None
        assert memory_id in edge['memory_ids']
        print(f"✅ Edge contains memory_id before deletion")
        
        # Delete the memory
        memories_db.delete_memory(test_user_id, memory_id)
        print(f"Deleted memory: {memory_id}")
        
        # Verify edge was deleted (orphaned)
        edges = kg_db.get_knowledge_edges(test_user_id)
        edge = next((e for e in edges if e['id'] == edge_id), None)
        assert edge is None
        print(f"✅ Orphaned edge was deleted")

    def test_partial_memory_deletion_updates_but_preserves(self, test_user_id, cleanup_test_data):
        """Test that deleting one memory from a node with multiple memories updates but preserves the node"""
        print(f"\n🧪 Testing partial cleanup (node with multiple memories)")
        
        # Create two test memories
        memory1_id = str(uuid.uuid4())
        memory1_data = {
            'id': memory1_id,
            'content': 'First memory about Paris',
            'created_at': datetime.now(timezone.utc),
            'user_review': True,
            'scoring': 1.0,
            'category': 'interesting',
            'visibility': 'private'
        }
        memories_db.create_memory(test_user_id, memory1_data)
        
        memory2_id = str(uuid.uuid4())
        memory2_data = {
            'id': memory2_id,
            'content': 'Second memory about Paris',
            'created_at': datetime.now(timezone.utc),
            'user_review': True,
            'scoring': 1.0,
            'category': 'interesting',
            'visibility': 'private'
        }
        memories_db.create_memory(test_user_id, memory2_data)
        print(f"Created memories: {memory1_id}, {memory2_id}")
        
        # Create a node linked to both memories
        node_id = str(uuid.uuid4())
        node_data = {
            'id': node_id,
            'label': 'Paris',
            'node_type': 'place',
            'aliases': [],
            'memory_ids': [memory1_id, memory2_id]
        }
        kg_db.upsert_knowledge_node(test_user_id, node_data)
        print(f"Created node with both memory_ids")
        
        # Verify node has both memory_ids
        node = kg_db.get_knowledge_node(test_user_id, node_id)
        assert memory1_id in node['memory_ids']
        assert memory2_id in node['memory_ids']
        assert len(node['memory_ids']) == 2
        print(f"✅ Node has both memory_ids")
        
        # Delete only the first memory
        memories_db.delete_memory(test_user_id, memory1_id)
        print(f"Deleted first memory: {memory1_id}")
        
        # Verify node still exists but only has memory2_id
        node = kg_db.get_knowledge_node(test_user_id, node_id)
        assert node is not None
        assert memory1_id not in node['memory_ids']
        assert memory2_id in node['memory_ids']
        assert len(node['memory_ids']) == 1
        print(f"✅ Node preserved with updated memory_ids")

    def test_orphaned_edge_deletion_when_source_node_deleted(self, test_user_id, cleanup_test_data):
        """Test that edges are deleted when their source node is deleted"""
        print(f"\n🧪 Testing edge deletion when source node is deleted")
        
        # Create memories
        memory1_id = str(uuid.uuid4())
        memory1_data = {
            'id': memory1_id,
            'content': 'John lives in Paris',
            'created_at': datetime.now(timezone.utc),
            'user_review': True,
            'scoring': 1.0,
            'category': 'interesting',
            'visibility': 'private'
        }
        memories_db.create_memory(test_user_id, memory1_data)
        
        memory2_id = str(uuid.uuid4())
        memory2_data = {
            'id': memory2_id,
            'content': 'Paris is beautiful',
            'created_at': datetime.now(timezone.utc),
            'user_review': True,
            'scoring': 1.0,
            'category': 'interesting',
            'visibility': 'private'
        }
        memories_db.create_memory(test_user_id, memory2_data)
        
        # Create nodes (John only from memory1, Paris from both)
        node1_id = str(uuid.uuid4())
        node1_data = {
            'id': node1_id,
            'label': 'John',
            'node_type': 'person',
            'aliases': [],
            'memory_ids': [memory1_id]
        }
        kg_db.upsert_knowledge_node(test_user_id, node1_data)
        
        node2_id = str(uuid.uuid4())
        node2_data = {
            'id': node2_id,
            'label': 'Paris',
            'node_type': 'place',
            'aliases': [],
            'memory_ids': [memory1_id, memory2_id]
        }
        kg_db.upsert_knowledge_node(test_user_id, node2_data)
        
        # Create edge from memory1
        edge_data = {
            'source_id': node1_id,
            'target_id': node2_id,
            'label': 'lives in',
            'memory_ids': [memory1_id]
        }
        kg_db.upsert_knowledge_edge(test_user_id, edge_data)
        edge_id = f"{node1_id}_lives in_{node2_id}"
        print(f"Created edge: {edge_id}")
        
        # Delete memory1 (should delete John node and the edge)
        memories_db.delete_memory(test_user_id, memory1_id)
        print(f"Deleted memory: {memory1_id}")
        
        # Verify John node is deleted (was only in memory1)
        node1 = kg_db.get_knowledge_node(test_user_id, node1_id)
        assert node1 is None
        print(f"✅ Source node (John) deleted")
        
        # Verify Paris node still exists (also in memory2)
        node2 = kg_db.get_knowledge_node(test_user_id, node2_id)
        assert node2 is not None
        assert memory2_id in node2['memory_ids']
        print(f"✅ Target node (Paris) preserved")
        
        # Verify edge is deleted (source node was deleted)
        edges = kg_db.get_knowledge_edges(test_user_id)
        edge = next((e for e in edges if e['id'] == edge_id), None)
        assert edge is None
        print(f"✅ Edge deleted because source node was deleted")

    def test_delete_all_memories_clears_graph(self, test_user_id, cleanup_test_data):
        """Test that deleting all memories clears the entire knowledge graph"""
        print(f"\n🧪 Testing delete all memories clears knowledge graph")
        
        # Create multiple memories with graph
        memory1_id = str(uuid.uuid4())
        memory1_data = {
            'id': memory1_id,
            'content': 'Test memory 1',
            'created_at': datetime.now(timezone.utc),
            'user_review': True,
            'scoring': 1.0,
            'category': 'interesting',
            'visibility': 'private'
        }
        memories_db.create_memory(test_user_id, memory1_data)
        
        memory2_id = str(uuid.uuid4())
        memory2_data = {
            'id': memory2_id,
            'content': 'Test memory 2',
            'created_at': datetime.now(timezone.utc),
            'user_review': True,
            'scoring': 1.0,
            'category': 'interesting',
            'visibility': 'private'
        }
        memories_db.create_memory(test_user_id, memory2_data)
        
        # Create nodes
        node1_id = str(uuid.uuid4())
        kg_db.upsert_knowledge_node(test_user_id, {
            'id': node1_id,
            'label': 'Node1',
            'node_type': 'concept',
            'memory_ids': [memory1_id]
        })
        
        node2_id = str(uuid.uuid4())
        kg_db.upsert_knowledge_node(test_user_id, {
            'id': node2_id,
            'label': 'Node2',
            'node_type': 'concept',
            'memory_ids': [memory2_id]
        })
        
        # Verify nodes exist
        graph = kg_db.get_knowledge_graph(test_user_id)
        assert len(graph['nodes']) >= 2
        print(f"Created {len(graph['nodes'])} nodes")
        
        # Delete all memories
        memories_db.delete_all_memories(test_user_id)
        print("Deleted all memories")
        
        # Verify knowledge graph is empty
        graph = kg_db.get_knowledge_graph(test_user_id)
        assert len(graph['nodes']) == 0
        assert len(graph['edges']) == 0
        print("✅ Knowledge graph completely cleared")


class TestCleanupFunction:
    """Test the clean_knowledge_graph_for_memory function directly"""

    def test_cleanup_returns_stats(self, test_user_id, cleanup_test_data):
        """Test that cleanup function returns statistics"""
        print(f"\n🧪 Testing cleanup function returns stats")
        
        # Create a memory and graph
        memory_id = str(uuid.uuid4())
        memory_data = {
            'id': memory_id,
            'content': 'Test memory',
            'created_at': datetime.now(timezone.utc),
            'user_review': True,
            'scoring': 1.0,
            'category': 'interesting',
            'visibility': 'private'
        }
        memories_db.create_memory(test_user_id, memory_data)
        
        node_id = str(uuid.uuid4())
        kg_db.upsert_knowledge_node(test_user_id, {
            'id': node_id,
            'label': 'TestNode',
            'node_type': 'concept',
            'memory_ids': [memory_id]
        })
        
        # Call cleanup directly
        stats = kg_db.clean_knowledge_graph_for_memory(test_user_id, memory_id)
        
        # Verify stats structure
        assert 'nodes_updated' in stats
        assert 'nodes_deleted' in stats
        assert 'edges_updated' in stats
        assert 'edges_deleted' in stats
        
        # Should have deleted 1 node
        assert stats['nodes_deleted'] == 1
        print(f"✅ Cleanup returned stats: {stats}")


# For manual testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print("KNOWLEDGE GRAPH MEMORY DELETION TESTS")
    print("="*60)
    print("\nOptional: Set TEST_USER_ID environment variable")
    print("  export TEST_USER_ID='your-test-user-id'\n")
    print("Then run: pytest backend/tests/integration/test_knowledge_graph_memory_deletion.py -v -s")
    print("="*60 + "\n")
