from pathlib import Path

from flask import Flask
from flask_migrate import Migrate

from config import Config
from models import db

from models.usuario import Usuario
from models.cliente import Cliente
from models.area_juridica import AreaJuridica
from models.status_caso import StatusCaso
from models.caso import Caso
from models.documento_caso import DocumentoCaso
from models.processo import Processo
from models.honorario import (
    HonorarioCaso,
    ParcelaHonorario,
)
from models.atendimento_caso import AtendimentoCaso
from models.evento_agenda import EventoAgenda
from models.modelo_documento import ModeloDocumento
from models.evento_caso import EventoCaso
from models.formulario_modelo import FormularioModelo
from models.pergunta_formulario import PerguntaFormulario
from models.formulario_caso import FormularioCaso
from models.resposta_formulario import RespostaFormulario


from routes.auth import auth_bp, login_manager
from routes.dashboard import dashboard_bp
from routes.clientes import clientes_bp
from routes.casos import casos_bp
from routes.documentos import documentos_bp
from routes.documentos_caso import documentos_caso_bp
from routes.cobrancas import cobrancas_bp
from routes.processos import processos_bp
from routes.honorarios import honorarios_bp
from routes.atendimentos import atendimentos_bp
from routes.agenda import agenda_bp
from routes.modelos import modelos_bp
from routes.gerador_documentos import gerador_documentos_bp
from routes.regras_modelo import regras_modelo_bp
from routes.formularios import formularios_bp
from routes.perguntas_formulario import perguntas_formulario_bp
from routes.formularios_caso import formularios_caso_bp

from seed.dados_iniciais import criar_dados_iniciais


migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Path(app.instance_path).mkdir(
        parents=True,
        exist_ok=True,
    )

    Path(app.config["UPLOAD_FOLDER"]).mkdir(
        parents=True,
        exist_ok=True,
    )

    pasta_modelos = (
        Path(app.config["UPLOAD_FOLDER"])
        / "modelos_documentos"
    )

    pasta_modelos.mkdir(
        parents=True,
        exist_ok=True,
    )

    db.init_app(app)

    migrate.init_app(
        app,
        db,
    )

    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(casos_bp)
    app.register_blueprint(documentos_bp)
    app.register_blueprint(documentos_caso_bp)
    app.register_blueprint(cobrancas_bp)
    app.register_blueprint(processos_bp)
    app.register_blueprint(honorarios_bp)
    app.register_blueprint(atendimentos_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(modelos_bp)
    app.register_blueprint(gerador_documentos_bp)
    app.register_blueprint(regras_modelo_bp)
    app.register_blueprint(
        formularios_bp
    )
    app.register_blueprint(
        perguntas_formulario_bp
    )
    app.register_blueprint(
        formularios_caso_bp
    )

    with app.app_context():
        db.create_all()
        criar_usuario_inicial()
        criar_dados_iniciais()

    return app


def criar_usuario_inicial():
    usuario_existente = Usuario.query.filter_by(
        email="admin@local",
    ).first()

    if usuario_existente:
        return

    usuario = Usuario(
        nome="Administrador",
        email="admin@local",
        perfil=Usuario.PERFIL_ADMIN,
        ativo=True,
    )

    usuario.definir_senha(
        "Admin@123",
    )

    db.session.add(usuario)
    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(
        debug=True,
    )