"""PostgreSQL grants and forced tenant policies. Run only as bootstrap owner."""
from psycopg import sql
from server.database import PRIVATE_TABLES

def apply_security(connection):
    connection.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
    connection.execute('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC')
    connection.execute('GRANT USAGE ON SCHEMA public TO h4t_auth,h4t_app,h4t_ingest,h4t_platform')
    for role in ['h4t_auth','h4t_app','h4t_ingest','h4t_platform']:
        connection.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}').format(sql.Identifier(role)))
    connection.execute('GRANT SELECT,INSERT ON users TO h4t_auth')
    connection.execute('GRANT SELECT,INSERT,DELETE ON sessions TO h4t_auth')
    connection.execute('GRANT SELECT(id,name,bot_id,created),INSERT ON companies TO h4t_auth')
    connection.execute('GRANT SELECT,INSERT ON channels TO h4t_auth')
    connection.execute('GRANT INSERT ON subscriptions TO h4t_auth')
    connection.execute('GRANT SELECT ON visitor_tokens,schema_migrations,public_assistant_appearance TO h4t_auth')
    connection.execute('GRANT SELECT,UPDATE ON companies,channels TO h4t_app')
    for table in PRIVATE_TABLES:
        connection.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON {} TO h4t_app').format(sql.Identifier(table)))
    connection.execute('GRANT SELECT ON channels TO h4t_ingest')
    connection.execute('GRANT INSERT,SELECT(id) ON channel_events TO h4t_ingest')
    connection.execute('GRANT SELECT ON platform_company_metadata TO h4t_platform')
    for table in ['companies','channels'] + PRIVATE_TABLES:
        ident=sql.Identifier(table)
        column=sql.Identifier('id' if table=='companies' else 'company_id')
        connection.execute(sql.SQL('ALTER TABLE {} ENABLE ROW LEVEL SECURITY').format(ident))
        connection.execute(sql.SQL('ALTER TABLE {} FORCE ROW LEVEL SECURITY').format(ident))
        connection.execute(sql.SQL('DROP POLICY IF EXISTS tenant_scope ON {}').format(ident))
        connection.execute(sql.SQL("CREATE POLICY tenant_scope ON {} TO h4t_app USING ({}=current_setting('h4t.company_id',true)) WITH CHECK ({}=current_setting('h4t.company_id',true))").format(ident,column,column))
    # Auth reads only tokens and allowlisted company/routing metadata, never payloads.
    for table in ['companies','channels','visitor_tokens']:
        ident=sql.Identifier(table)
        connection.execute(sql.SQL('DROP POLICY IF EXISTS auth_read ON {}').format(ident))
        connection.execute(sql.SQL('CREATE POLICY auth_read ON {} FOR SELECT TO h4t_auth USING (true)').format(ident))
    for table in ['companies','channels','subscriptions']:
        ident=sql.Identifier(table)
        connection.execute(sql.SQL('DROP POLICY IF EXISTS auth_create ON {}').format(ident))
        connection.execute(sql.SQL('CREATE POLICY auth_create ON {} FOR INSERT TO h4t_auth WITH CHECK (true)').format(ident))
    connection.execute('DROP POLICY IF EXISTS webhook_route ON channels')
    connection.execute('CREATE POLICY webhook_route ON channels FOR SELECT TO h4t_ingest USING (true)')
    connection.execute('DROP POLICY IF EXISTS webhook_insert ON channel_events')
    connection.execute('CREATE POLICY webhook_insert ON channel_events FOR INSERT TO h4t_ingest WITH CHECK (true)')
    connection.execute('DROP POLICY IF EXISTS webhook_dedupe ON channel_events')
    connection.execute('CREATE POLICY webhook_dedupe ON channel_events FOR SELECT TO h4t_ingest USING (true)')
