"""Create CheckDocument table and update PlagiarismCheck

Revision ID: create_check_documents
Revises: 11c6713d0de7
Create Date: 2025-09-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'create_check_documents'
down_revision = '11c6713d0de7'
branch_labels = None
depends_on = None


def upgrade():
    """Create CheckDocument table and migrate data."""
    
    # Create check_documents table
    op.create_table(
        'check_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('object_id', sa.String(255), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('object_id')
    )
    op.create_index('ix_check_documents_id', 'check_documents', ['id'])
    op.create_index('ix_check_documents_user_id', 'check_documents', ['user_id'])
    
    # Migrate existing UserDocuments that have plagiarism checks to CheckDocuments
    # First, get connection for data migration
    connection = op.get_bind()
    
    # Find UserDocuments that have associated PlagiarismChecks
    result = connection.execute(sa.text("""
        SELECT DISTINCT ud.id, ud.user_id, ud.title, ud.object_id, ud.content_type, ud.created_at, ud.updated_at
        FROM user_documents ud
        INNER JOIN plagiarism_checks pc ON pc.user_document_id = ud.id
    """))
    
    check_documents_to_create = []
    plagiarism_updates = []
    
    for row in result:
        # Prepare CheckDocument creation
        check_documents_to_create.append({
            'user_id': row.user_id,
            'title': row.title,
            'object_id': row.object_id,
            'content_type': row.content_type,
            'status': 'active',
            'created_at': row.created_at,
            'updated_at': row.updated_at
        })
        
        # Track original user_document_id for plagiarism_checks update
        plagiarism_updates.append({
            'old_user_document_id': row.id,
            'object_id': row.object_id  # We'll use this to find the new check_document_id
        })
    
    # Insert CheckDocuments
    if check_documents_to_create:
        op.bulk_insert(
            sa.table('check_documents',
                sa.column('user_id'),
                sa.column('title'),
                sa.column('object_id'),
                sa.column('content_type'),
                sa.column('status'),
                sa.column('created_at'),
                sa.column('updated_at')
            ),
            check_documents_to_create
        )
    
    # Add new check_document_id column to plagiarism_checks
    op.add_column('plagiarism_checks', sa.Column('check_document_id', sa.Integer(), nullable=True))
    
    # Update plagiarism_checks to reference CheckDocuments instead of UserDocuments
    for update_info in plagiarism_updates:
        # Find the new check_document_id based on object_id
        result = connection.execute(sa.text("""
            SELECT id FROM check_documents WHERE object_id = :object_id
        """), {'object_id': update_info['object_id']})
        
        check_document_row = result.fetchone()
        if check_document_row:
            # Update plagiarism_checks to use check_document_id
            connection.execute(sa.text("""
                UPDATE plagiarism_checks 
                SET check_document_id = :check_document_id 
                WHERE user_document_id = :old_user_document_id
            """), {
                'check_document_id': check_document_row.id,
                'old_user_document_id': update_info['old_user_document_id']
            })
    
    # Make check_document_id NOT NULL after migration
    op.alter_column('plagiarism_checks', 'check_document_id', nullable=False)
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_plagiarism_checks_check_document_id',
        'plagiarism_checks', 'check_documents',
        ['check_document_id'], ['id']
    )
    
    # Remove old user_document_id column
    op.drop_constraint('plagiarism_checks_user_document_id_fkey', 'plagiarism_checks', type_='foreignkey')
    op.drop_column('plagiarism_checks', 'user_document_id')
    
    # Clean up UserDocuments that were migrated to CheckDocuments
    for update_info in plagiarism_updates:
        connection.execute(sa.text("""
            DELETE FROM user_documents WHERE id = :user_document_id
        """), {'user_document_id': update_info['old_user_document_id']})


def downgrade():
    """Revert CheckDocument changes."""
    
    # Add back user_document_id column
    op.add_column('plagiarism_checks', sa.Column('user_document_id', sa.Integer(), nullable=True))
    
    # This is a simplified downgrade - in practice, you'd need to migrate data back
    # For now, just clean up the schema changes
    
    # Remove check_document_id foreign key and column
    op.drop_constraint('fk_plagiarism_checks_check_document_id', 'plagiarism_checks', type_='foreignkey')
    op.drop_column('plagiarism_checks', 'check_document_id')
    
    # Make user_document_id NOT NULL again
    op.alter_column('plagiarism_checks', 'user_document_id', nullable=False)
    
    # Re-add foreign key constraint
    op.create_foreign_key(
        'plagiarism_checks_user_document_id_fkey',
        'plagiarism_checks', 'user_documents',
        ['user_document_id'], ['id']
    )
    
    # Drop check_documents table
    op.drop_index('ix_check_documents_user_id', 'check_documents')
    op.drop_index('ix_check_documents_id', 'check_documents')
    op.drop_table('check_documents')