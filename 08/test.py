L.prepare()
L.start()
L.sql("SELECT rolname,rolcanlogin,rolsuper FROM pg_roles ORDER BY 1;")
L.sql("""GRANT USAGE ON SCHEMA public TO app_laeser;
GRANT SELECT ON hemmelig_data TO app_laeser;
SET ROLE app_laeser;
SELECT current_user,count(*) FROM hemmelig_data;
RESET ROLE;""",expect=r'app_laeser\|6')
ins="INSERT INTO hemmelig_data(navn,hemmelighed,ejer) VALUES('test','syntetisk','app_skriver');"
def deny(role,sql):
    L.sql('SET ROLE '+role+';\n'+sql,fail='42501.*permission denied for table')
deny('app_laeser',ins)
L.sql("GRANT SELECT,INSERT,UPDATE ON hemmelig_data TO app_skriver;\nGRANT USAGE,SELECT ON SEQUENCE hemmelig_data_id_seq TO app_skriver;\nGRANT ALL ON hemmelig_data TO app_admin;\nSET ROLE app_skriver;\n"+ins+"\nUPDATE hemmelig_data SET navn='ændret' WHERE ejer=current_user;",expect='UPDATE 1')
deny('app_skriver',"DELETE FROM hemmelig_data WHERE ejer=current_user;")
L.sql("SET ROLE app_admin;\nBEGIN;\nDELETE FROM hemmelig_data WHERE ejer='app_skriver';\nROLLBACK;",expect='DELETE 1')
L.sql('REVOKE UPDATE ON hemmelig_data FROM app_skriver;')
deny('app_skriver',"UPDATE hemmelig_data SET navn='rettet' WHERE ejer=current_user;")
L.sql("""CREATE ROLE tabelejer NOLOGIN NOSUPERUSER NOBYPASSRLS;
CREATE ROLE revision NOLOGIN NOSUPERUSER BYPASSRLS;
GRANT SELECT ON hemmelig_data TO revision;
ALTER TABLE hemmelig_data OWNER TO tabelejer;
ALTER TABLE hemmelig_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY ejer_policy ON hemmelig_data USING (ejer=current_user);
SET ROLE app_laeser;
SELECT navn,ejer FROM hemmelig_data ORDER BY id;
SELECT current_user,count(*),bool_and(ejer=current_user) FROM hemmelig_data;
RESET ROLE;
SET ROLE tabelejer;
SELECT current_user,count(*) FROM hemmelig_data;
RESET ROLE;
ALTER TABLE hemmelig_data FORCE ROW LEVEL SECURITY;
SET ROLE tabelejer;
SELECT current_user,count(*) FROM hemmelig_data;
RESET ROLE;
SET ROLE revision;
SELECT current_user,count(*) FROM hemmelig_data;
RESET ROLE;
SELECT current_user,count(*) FROM hemmelig_data;
SELECT grantee,privilege_type FROM information_schema.role_table_grants WHERE table_name='hemmelig_data' ORDER BY 1,2;""",expect=r'app_laeser\|2\|t.*tabelejer\|7.*tabelejer\|0.*revision\|7.*studie\|7')
pw=L.new_secret('reader.pass')
L.sql("ALTER ROLE app_laeser PASSWORD '"+pw+"';")
def real(query,fail=None):
    L.note('TCP / '+query)
    return L.run(['docker','exec','-i','-e','PGPASSWORD',L.cid,'psql','-h','postgres','-XAt','-v','ON_ERROR_STOP=1','-v','VERBOSITY=verbose','-U','app_laeser','-d','studiebase'],data=query,env={'PGPASSWORD':pw},fail=fail)
check(real("SELECT session_user,current_user,count(*),bool_and(ejer=current_user) FROM hemmelig_data;")== 'app_laeser|app_laeser|2|t','TCP-læsning')
for stmt in [ins,"UPDATE hemmelig_data SET navn='x' WHERE ejer=current_user;","DELETE FROM hemmelig_data WHERE ejer=current_user;"]:
    real(stmt,'42501.*permission denied for table')
