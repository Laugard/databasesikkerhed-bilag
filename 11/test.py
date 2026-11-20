L.prepare()
L.start()
L.sql("SELECT extname,extversion FROM pg_extension WHERE extname='pgcrypto';",expect=r'pgcrypto\|')
L.sql("""SELECT brugernavn,pg_typeof(cpr_krypteret),octet_length(cpr_krypteret),
 left(encode(cpr_krypteret,'hex'),16) AS binaer_praefiks
 FROM brugere_krypteret ORDER BY id LIMIT 3;""",expect=r'bruger1\|bytea')
key="'"+L.key+"'"
synt="'"+L.sample+"'"
password="'"+L.userpw+"1'"
L.secret.append(L.userpw+'1')
L.sql(f"""SELECT id,brugernavn,length(pgp_sym_decrypt(cpr_krypteret,{key})),length({synt}),
 starts_with(pgp_sym_decrypt(cpr_krypteret,{key}),{synt}),
 pgp_sym_decrypt(cpr_krypteret,{key})=({synt} || substring(brugernavn from 7)) AS matcher_brugernavn
 FROM brugere_krypteret ORDER BY id LIMIT 3;""")
L.sql(f"""SELECT count(*),bool_and(pgp_sym_decrypt(cpr_krypteret,{key})=({synt}||substring(brugernavn from 7))) FROM brugere_krypteret;
SELECT pgp_sym_encrypt({synt},{key})<>pgp_sym_encrypt({synt},{key});""",expect=r'100\|t\nt')
wrong=L.new_secret('wrong')
L.sql(f"SELECT pgp_sym_decrypt(cpr_krypteret,'{wrong}') FROM brugere_krypteret LIMIT 1;",fail='39000.*Wrong key or corrupt data')
L.sql(f"""SELECT length(kodehash),left(kodehash,2),crypt({password},kodehash)=kodehash,
 crypt('{wrong}',kodehash)=kodehash FROM brugere_krypteret WHERE brugernavn='bruger1';""",expect=r'60\|\$2\|t\|f')
q=f"SELECT count(*) FROM brugere_krypteret WHERE pgp_sym_decrypt(cpr_krypteret,{key})={synt}||'1';"
L.sql('EXPLAIN (ANALYZE,BUFFERS) '+q+'\n'+q,expect=r'Seq Scan.*\n1$')
