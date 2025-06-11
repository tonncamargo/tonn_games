from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jogadores.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'Eu-Amo-A-Ana-Paula'

db = SQLAlchemy(app)

# MODELOS
class Jogador(db.Model):
    __tablename__ = 'jogador'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    nick = db.Column(db.String(50), nullable=False, unique=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Jogador {self.nick}>'

class Jogo(db.Model):
    __tablename__ = 'jogo'
    id = db.Column(db.Integer, primary_key=True)
    data_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    data_fim = db.Column(db.DateTime, nullable=True)
    jogador_inicial_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    perdedor_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=True)

    jogador_inicial = db.relationship('Jogador', foreign_keys=[jogador_inicial_id], backref='jogos_iniciados')
    perdedor = db.relationship('Jogador', foreign_keys=[perdedor_id], backref='jogos_perdidos')
    rodadas = db.relationship('Rodada', backref='jogo', lazy=True, cascade='all, delete-orphan')

class Rodada(db.Model):
    __tablename__ = 'rodada'
    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey('jogo.id'), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    pontos = db.Column(db.JSON, nullable=False)

# ROTAS
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/historico')
def historico():
    jogos = Jogo.query.order_by(Jogo.data_inicio.desc()).all()
    return render_template('historico.html', jogos=jogos)

@app.route('/ranking')
def ranking():
    ranking = db.session.query(
        Jogador.nick,
        func.count(Jogo.id).filter(Jogo.perdedor_id == Jogador.id).label('derrotas')
    ).outerjoin(Jogo, Jogador.id == Jogo.perdedor_id)\
     .group_by(Jogador.id).order_by(func.count(Jogo.id).filter(Jogo.perdedor_id == Jogador.id)).all()

    return render_template('ranking.html', ranking=ranking)

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        nick = request.form['nick']

        if not nome or not nick:
            flash('Preencha todos os campos!', 'danger')
            return redirect(url_for('cadastro'))

        jogador_existente = Jogador.query.filter_by(nick=nick).first()
        if jogador_existente:
            flash(f'O nick "{nick}" já está em uso. Escolha outro.', 'danger')
            return redirect(url_for('cadastro'))

        novo_jogador = Jogador(nome=nome, nick=nick)
        db.session.add(novo_jogador)
        try:
            db.session.commit()
            flash('Jogador cadastrado com sucesso!', 'success')
            return redirect(url_for('cadastro'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao cadastrar jogador!', 'danger')
            return redirect(url_for('cadastro'))

    return render_template('cadastro.html')

@app.route('/jogadores')
def listar_jogadores():
    jogadores = Jogador.query.order_by(Jogador.data_cadastro.desc()).all()
    return render_template('jogadores.html', jogadores=jogadores)

@app.route('/deletar/<int:id>', methods=['POST'])
def deletar_jogador(id):
    jogador_para_excluir = Jogador.query.get_or_404(id)
    try:
        db.session.delete(jogador_para_excluir)
        db.session.commit()
        flash(f'Jogador {jogador_para_excluir.nick} excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir jogador {jogador_para_excluir.nick}!', 'danger')
    return redirect(url_for('listar_jogadores'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_jogador(id):
    jogador_editado = Jogador.query.get_or_404(id)

    if request.method == 'POST':
        nome = request.form['nome']
        nick = request.form['nick']

        if not nome or not nick:
            flash('Preencha todos os campos!', 'danger')
            return redirect(url_for('editar_jogador', id=id))

        if nick != jogador_editado.nick and Jogador.query.filter_by(nick=nick).first():
            flash(f'O nick "{nick}" já está em uso. Escolha outro.', 'danger')
            return redirect(url_for('editar_jogador', id=id))

        jogador_editado.nome = nome
        jogador_editado.nick = nick
        try:
            db.session.commit()
            flash(f'Dados de {jogador_editado.nick} atualizados com sucesso!', 'success')
            return redirect(url_for('listar_jogadores'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar dados do jogador!', 'danger')
            return redirect(url_for('editar_jogador', id=id))

    return render_template('editar_jogador.html', jogador=jogador_editado)

@app.route('/novo_jogo', methods=['GET', 'POST'])
def novo_jogo():
    jogadores = Jogador.query.order_by(Jogador.nome).all()

    if request.method == 'POST':
        selecionados = request.form.getlist('jogadores')
        embaralhador = request.form.get('jogador_inicial')

        if len(selecionados) < 2:
            flash('Selecione pelo menos 2 jogadores para iniciar um jogo.', 'warning')
            return redirect(url_for('novo_jogo'))

        if not embaralhador or embaralhador not in selecionados:
            flash('Selecione um jogador inicial válido.', 'warning')
            return redirect(url_for('novo_jogo'))

        novo_jogo = Jogo(jogador_inicial_id=int(embaralhador))
        try:
            db.session.add(novo_jogo)
            db.session.commit()
            flash('Novo jogo criado com sucesso!', 'success')
            return redirect(url_for('ver_jogo', id=novo_jogo.id))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar novo jogo!', 'danger')
            return redirect(url_for('novo_jogo'))

    return render_template('novo_jogo.html', jogadores=jogadores)

@app.route('/jogo/<int:id>', methods=['GET', 'POST'])
def ver_jogo(id):
    jogo_atual = Jogo.query.get_or_404(id)
    
    # Verifica se o jogo já terminou
    if jogo_atual.data_fim:
        flash('Este jogo já foi finalizado!', 'warning')
        return redirect(url_for('historico'))
    
    jogadores = Jogador.query.order_by(Jogador.nome).all()
    rodadas = Rodada.query.filter_by(jogo_id=id).order_by(Rodada.numero).all()

    totais = {}
    for r in rodadas:
        for id_jogador, pontos in r.pontos.items():
            id_jogador = int(id_jogador)
            totais[id_jogador] = totais.get(id_jogador, 0) + pontos

    if request.method == 'POST':
        pontos = {}
        for j in jogadores:
            valor = request.form.get(f'pontos_{j.id}')
            if valor and valor.strip():
                try:
                    pontos[j.id] = int(valor)
                except ValueError:
                    flash(f'Valor inválido para {j.nick}!', 'danger')
                    return redirect(url_for('ver_jogo', id=id))

        if not pontos:
            flash('Nenhum ponto foi registrado!', 'warning')
            return redirect(url_for('ver_jogo', id=id))

        nova_rodada = Rodada(
            jogo_id=id,
            numero=len(rodadas) + 1,
            pontos=pontos
        )
        try:
            db.session.add(nova_rodada)
            
            # Atualiza totais após adicionar a rodada
            for id_jogador, valor in pontos.items():
                totais[id_jogador] = totais.get(id_jogador, 0) + valor

            # Verifica se algum jogador atingiu 100 pontos
            for id_jogador, total in totais.items():
                if total >= 100:
                    jogo_atual.data_fim = datetime.utcnow()
                    jogo_atual.perdedor_id = id_jogador
                    db.session.commit()
                    flash(f'{Jogador.query.get(id_jogador).nick} perdeu o jogo!', 'danger')
                    return redirect(url_for('index'))
            
            db.session.commit()
            flash('Rodada registrada com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao registrar rodada!', 'danger')

        return redirect(url_for('ver_jogo', id=id))

    return render_template('ver_jogo.html', 
                         jogo=jogo_atual, 
                         jogadores=jogadores, 
                         rodadas=rodadas, 
                         totais=totais)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)