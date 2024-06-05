# TEST

Utilisation

Générer la clé de chiffrement : 

Exemple

```
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

I0hqk3P_7GePKzed8-Q5WB9R52tOC1HtLzwFqleUD4E=
```

Build le docker 
```
docker compose build

docker compose ud -d
```