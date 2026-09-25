# pip install flask flask-sqlalchemy
from flask import Flask, render_template, redirect, url_for, request, session, flash
from datetime import timedelta, datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

## Configuração da base de dados
app.secret_key = 'diogo1234!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

## Limite de tempo por sessão (5 minutos)
app.permanent_session_lifetime = timedelta(days=1)

# Criação do objeto SQLAlchemy
db = SQLAlchemy(app)

class Cargo (db.Model):
    __tablename__ = 'cargos'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(50), nullable=False)


class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    cargo = db.Column(db.Integer, db.ForeignKey('cargos.id'), nullable=False)


    def __init__(self, nome ,email, password, cargo=1):
        self.nome = nome
        self.email = email
        self.password = password
        self.cargo = cargo


class Tarefas(db.Model):
    __tablename__ = 'tarefas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tarefa = db.Column(db.String(100), nullable=False)
    dataLimite = db.Column(db.DateTime)
    descricao = db.Column(db.String(255))
    estado = db.Column(db.Boolean, default=False)
    idUtilizador = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __init__(self, tarefa, dataLimite=None, descricao=None, idUtilizador=None, estado=False):
        self.tarefa = tarefa
        self.dataLimite = dataLimite
        self.descricao = descricao
        self.idUtilizador = idUtilizador
        self.estado = estado


## Criar as tabelas na base de dados se não existirem
with app.app_context():
    db.create_all()
    if Cargo.query.count() == 0:
        cargo1 = Cargo(nome="User")
        cargo2 = Cargo(nome="Admin")

        # Adiciona e salva no banco de dados
        db.session.add_all([cargo1, cargo2])
        db.session.commit()
        print("Registros iniciais criados com sucesso!")



@app.route('/concluir_tarefa/<int:id>')
def concluir_tarefa(id):
    if "user" not in session:
        return redirect(url_for('login'))

    tarefa = Tarefas.query.get_or_404(id)
    tarefa.estado = not tarefa.estado
    db.session.commit()
    return redirect(url_for('tarefas', email=session['user']))


@app.route('/eliminar_tarefa/<int:id>', methods=['POST'])
def eliminar_tarefa(id):
    if "user" not in session:
        return redirect(url_for('login'))
    db.session.query(Tarefas).filter(Tarefas.id == id).delete()
    db.session.commit()
    return redirect(url_for('tarefas', email=session['user']))


@app.route('/editar_tarefa/<int:id>', methods=['POST'])
def editar_tarefa(id):
    if "user" not in session:
        return redirect(url_for('login'))

    tarefa = Tarefas.query.get_or_404(id)
    tarefa.tarefa = request.form.get('tarefa')
    tarefa.descricao = request.form.get('descricao')

    db.session.commit()
    flash("Tarefa atualizada!")
    return redirect(url_for('tarefas', email=session['user']))

@app.route('/registar', methods=['GET', 'POST'])
def registar():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        password = request.form.get('password')
        password1 = request.form.get('password1')

        if not nome or not email or not password or not password1:
            flash("Todos os campos obrigatórios devem ser preenchidos.")
            return redirect(url_for('registar'))

        if password != password1:
            flash("As passwords não coincidem.")
            return redirect(url_for('registar'))

        user = Users.query.filter_by(email=email).first()
        if user:
            flash("Email já registado.")
            return redirect(url_for('registar'))

        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = Users(nome=nome, email=email, password=password_hash, cargo=1    )
        db.session.add(new_user)
        db.session.commit()

        flash("Utilizador registado com sucesso.")
        return redirect(url_for('login'))

    return render_template('registar.html')


@app.route('/tarefas/<email>', methods=['GET', 'POST'])
def tarefas(email):
    # 1. Verificar se o utilizador tem sessão iniciada
    if "user" not in session:
        flash("Tem de efetuar o login.")
        return redirect(url_for('login'))

    # 2. Impedir que um utilizador aceda à página/tarefas de outro
    if session["user"] != email:
        flash("Acesso não autorizado.")
        return redirect(url_for('tarefas', email=session["user"]))

    utilizador = Users.query.filter_by(email=email).first_or_404()

    if request.method == 'POST':
        tarefa_titulo = request.form.get('tarefa')
        data_limite_str = request.form.get('dataLimite')
        descricao = request.form.get('descricao')

        # Tratamento da data recebida no formulário
        data_limite_obj = None
        if data_limite_str:
            try:
                data_limite_obj = datetime.strptime(data_limite_str, '%Y-%m-%d')
            except ValueError:
                data_limite_obj = None

        if tarefa_titulo:
            nova_tarefa = Tarefas(
                tarefa=tarefa_titulo,
                dataLimite=data_limite_obj,
                descricao=descricao,
                idUtilizador=utilizador.id
            )
            db.session.add(nova_tarefa)
            db.session.commit()

            flash("Tarefa adicionada com sucesso.")
            return redirect(url_for('tarefas', email=email))

    lista_tarefas = Tarefas.query.filter_by(idUtilizador=utilizador.id).order_by(Tarefas.estado.asc()).all()
    return render_template('tarefas.html', email=utilizador.email, tarefas=lista_tarefas)

@app.route('/view')
def view():
    if "user" not in session:
        flash("Tem de efetuar o login.")
        return redirect(url_for('login'))

    todos_utilizadores = Users.query.all()
    return render_template('view.html', utilizadores=todos_utilizadores)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        utilizador = Users.query.filter_by(email=email).first()

        if utilizador and check_password_hash(utilizador.password, password):
            session.permanent = True
            session['user'] = utilizador.email
            session['id'] = utilizador.id
            session['cargo_id'] = utilizador.cargo
            flash("Login com sucesso.")
            return redirect(url_for('index'))
        else:
            flash("Email ou password incorreto.")

    return render_template('login.html')


@app.route("/logout")
def logout():
    session.clear()
    flash("Logout com sucesso.")
    return redirect(url_for('index'))


@app.route('/')
def index():
    if "user" not in session:
        return redirect(url_for('login'))

    user_id = session['id']
    tarefas_utilizador = Tarefas.query.filter_by(idUtilizador=user_id).count()
    total_concluidas = Tarefas.query.filter_by(idUtilizador=user_id, estado=True).count()
    total_pendentes = Tarefas.query.filter_by(idUtilizador=user_id, estado=False).count()

    return render_template(
        'index.html',
        tarefas=tarefas_utilizador,
        concluidas=total_concluidas,
        pendentes=total_pendentes
    )


if __name__ == '__main__':
    app.run(debug=True)