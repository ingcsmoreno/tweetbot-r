import requests
from urllib import parse
from requests.auth import HTTPBasicAuth
import json

from requests.models import Response
from mediaclasses import *

class DBManager:
    host = None
    port = None
    database = None
    user = None
    password = None
    baseURL = None
    getURL = None
    batchURL = None
    
    def __init__ (self, host='http://localhost', port=2480, database='portico', user='admin', password='admin'):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.baseURL = host+":"+str(port)
        
        self.getURL = parse.urljoin(self.baseURL,"/query/"+self.database+"/sql/") 
        self.batchURL = parse.urljoin(self.baseURL,"/batch/"+self.database)

    def execGETQuery (self,query):
        """Ejecuta la consulta pasada por parámetro y devuelve los datos en formato JSON.
        Args:
            query (string): Query a ejecutar
        Returns:
            string: JSON con los datos devueltos
        """    
        req_query = parse.urljoin(self.getURL,query)
        response = requests.get(req_query, auth=HTTPBasicAuth(self.user, self.password))
        if (response.ok):
            # Convertir la cadena de bytes en un string, con encode utf-8
            parsed = json.loads(response.content.decode("utf-8"))
            # el response tiene un elemento llamado result, que contiene los valores devueltos
            result = parsed['result']
        else:
            result = None
        return result

    def insertLibroAutor (self, libro: Libro, autor : Autor):
        '''Inserta un libro y su autor correspondiende, obviando los datos que ya existan
        '''
        json_libro = json.dumps(libro.__dict__)
        json_autor = json.dumps(autor.__dict__)
        script = """BEGIN; 
    LET libro = SELECT from Libro where titulo.toUpperCase() = '{titulolibro}'.toUpperCase();
    if ($libro.size() = 0) {{
        LET libro = CREATE VERTEX Libro SET titulo = '{titulolibro}';
    }}
    LET autor = SELECT from Autor where nombre.toUpperCase() = '{nombreautor}'.toUpperCase();
    if ($autor.size() = 0) {{
        LET autor = CREATE VERTEX Autor SET nombre = '{nombreautor}';
    }}
    LET autorDe = match
            {{class:Autor, as: a, where: (nombre.toUpperCase() = '{nombreautor}'.toUpperCase())}}.out('autorDe') 
            {{class:Libro, as: l, where: (titulo.toUpperCase() = '{titulolibro}'.toUpperCase())}} return a;
    if ($autorDe.size() = 0) {{
        CREATE EDGE autorDe FROM $autor TO $libro RETRY 100;
    }}
    CREATE EDGE esGenero from $libro to (select from Genero where genero = 'Sci Fi');
    COMMIT;"""
        script = script.format(titulolibro=libro.titulo,nombreautor=autor.nombre)
        operaciones = [{"type":"script","language":"sql","script":[script]}]
        data = {"transaction":True,"operations":operaciones}
        response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
        return response

    def updateLibro (self, libro: Libro):
        ''' Actualiza los datos de un libro (buscando por titulo)
        '''
        json_libro = json.dumps(libro.__dict__)
        
        script = """BEGIN; 
    LET libro = SELECT from Libro where titulo.toUpperCase() = '{titulolibro}'.toUpperCase();
    if ($libro.size() = 1) {{
        UPDATE Libro SET
        paginas = {paginas},
        publicado = {publicado},
        sinopsis = '{sinopsis}',
        urlDownload = '{urlDownload}',
        urlPortada = '{urlPortada}'
        WHERE titulo = '{titulolibro}';
    }}
    COMMIT;"""
        script = script.format(
            titulolibro=libro.titulo,
            paginas=libro.paginas,
            publicado=libro.publicado,
            sinopsis=libro.sinopsis,
            urlDownload=libro.urlDownload,
            urlPortada=libro.urlPortada
            )
        operaciones = [{"type":"script","language":"sql","script":[script]}]
        data = {"transaction":True,"operations":operaciones}
        response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
        return response

    def deleteAuthorAndBooks(self,autor: Autor):
        ''' Actualiza los datos de un libro (buscando por titulo)
        '''
        script = """BEGIN; 
    DELETE VERTEX Libro WHERE in('autorDe').nombre = '{autor}';
    DELETE VERTEX Autor WHERE nombre = '{autor}';
    COMMIT;"""
        script = script.format(
            autor=autor.nombre
            )
        operaciones = [{"type":"script","language":"sql","script":[script]}]
        data = {"transaction":True,"operations":operaciones}
        response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
        return response 

    def insertTwitt (self, id : str, text : str, author_id : str, conversation_id : str, in_reply_to_user_id : str):
        script = """
    BEGIN; 
    LET twitt = SELECT from Twitt where id = '{id}';
    if ($twitt.size() = 0) {{
        CREATE VERTEX Twitt SET
        id = '{id}',
        text = '{text}',
        author_id = '{author_id}',
        conversation_id = '{conversation_id}',
        in_reply_to_user_id = '{in_reply_to_user_id}';
    }}
    COMMIT;"""
        script = script.format(
            id=id,
            text=text,
            author_id=author_id,
            conversation_id=conversation_id,
            in_reply_to_user_id=in_reply_to_user_id
            )
        operaciones = [{"type":"script","language":"sql","script":[script]}]
        data = {"transaction":True,"operations":operaciones}
        response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
        return response 

    def insertTwittRelation (self, id_source : str, id_destination : str, relation_type : str):
        script = """
    BEGIN; 
    CREATE EDGE {tipo_edge} from (select from Twitt where id = '{id_source}') to (select from Twitt where id = '{id_destination}');
    COMMIT;"""
        if (relation_type == 'replied_to'):
            tipo_edge = 'TwittReply'
        elif (relation_type == 'quoted'):
            tipo_edge = 'TwittCite'
        elif (relation_type == 'retweeted'):
            tipo_edge = 'TwittRetweet'
        else:
            tipo_edge = 'E'
        script = script.format(
            tipo_edge=tipo_edge,
            id_source=id_source,
            id_destination=id_destination
            )
        operaciones = [{"type":"script","language":"sql","script":[script]}]
        data = {"transaction":True,"operations":operaciones}
        response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
        return response

    def insertMovie (self, movie : Pelicula):
        '''Inserta una pelicula
        '''
        script = """
    LET movie = SELECT from Pelicula where id = '{id}';
    if ($movie.size() = 0) {{
        LET movie = CREATE VERTEX Pelicula 
        SET titulo = '{titulopelicula}',
            id = '{id}',
            imdb_id = '{imdb_id}',
            anio = '{anio}',
            argumento = '{argumento}',
            tagline = '{tagline}',
            urlPoster = '{urlPoster}';
        CREATE EDGE esGenero from $movie to (select from Genero where genero = 'Sci Fi');
    }}"""
        script = script.format(
            id=movie.id,
            titulopelicula=movie.titulo.replace("'","`"),
            imdb_id=movie.imdb_id,
            anio=movie.anio,
            argumento=movie.argumento.replace("'","`"),
            tagline=movie.tagline.replace("'","`"),
            urlPoster=movie.urlPoster
            )
        operaciones = [{"type":"script","language":"sql","script":[script]}]
        data = {"transaction":True,"operations":operaciones}
        response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
        return response

    def insertDirectorMovie (self, movie : Pelicula, director : Director):
        '''Inserta un director, y lo asocia a la película
        '''
        script = """BEGIN;
        LET movie = SELECT from Pelicula where id = '{idmovie}';
        if ($movie.size() > 0) {{
            LET director = SELECT from Director where nombre.toUpperCase() = '{nombredirector}'.toUpperCase();
            if ($director.size() = 0) {{
                LET director = CREATE VERTEX Director SET nombre = '{nombredirector}';
            }}
            LET directorDe = match
                    {{class:Director, as: d, where: (nombre.toUpperCase() = '{nombredirector}'.toUpperCase())}}.out('directorDe') 
                    {{class:Pelicula, as: p, where: (id = '{idmovie}')}} return a;
            if ($directorDe.size() = 0) {{
                CREATE EDGE directorDe FROM $director TO $movie RETRY 100;
            }}
        }}
        COMMIT;"""
        script = script.format(
            idmovie=movie.id,
            nombredirector=director.nombre
            )
        operaciones = [{"type":"script","language":"sql","script":[script]}]
        data = {"transaction":True,"operations":operaciones}
        response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
        return response

    def insertActoresPersonajesMovie (self, movie : Pelicula, actores : list):
        '''Inserta una pelicula
        '''
        script_base = """BEGIN;
        LET movie = SELECT from Pelicula where id = '{idmovie}';
        if ($movie.size() > 0) {{
            LET actor = SELECT from Actor where nombre.toUpperCase() = '{nombreactor}'.toUpperCase();
            if ($actor.size() = 0) {{
                LET actor = CREATE VERTEX Actor SET nombre = '{nombreactor}';
            }}
            LET actuoEn = match
                    {{class:Actor, as: a, where: (nombre.toUpperCase() = '{nombreactor}'.toUpperCase())}}.out('actuoEn') 
                    {{class:Pelicula, as: p, where: (id = '{idmovie}')}} return a;
            if ($actuoEn.size() = 0) {{
                CREATE EDGE actuoEn FROM $actor TO $movie RETRY 100;
            }}
            
            LET personaje = SELECT from Personaje where nombre.toUpperCase() = '{nombrepersonaje}'.toUpperCase();
            if ($personaje.size() = 0) {{
                LET personaje = CREATE VERTEX Personaje SET nombre = '{nombrepersonaje}';
            }}
            LET apareceEn = match
                    {{class:Personaje, as: p, where: (nombre.toUpperCase() = '{nombrepersonaje}'.toUpperCase())}}.out('apareceEn') 
                    {{class:Pelicula, as: m, where: (id = '{idmovie}')}} return a;
            if ($apareceEn.size() = 0) {{
                CREATE EDGE apareceEn FROM $personaje TO $movie RETRY 100;
            }}

            LET interpretoA = match
                    {{class:Actor, as: a, where: (nombre.toUpperCase() = '{nombreactor}'.toUpperCase())}}.out('interpretoA') 
                    {{class:Personaje, as: p, where: (nombre.toUpperCase() = '{nombrepersonaje}'.toUpperCase())}} return a;
            if ($interpretoA.size() = 0) {{
                CREATE EDGE interpretoA FROM $actor TO $personaje RETRY 100;
            }}
        }}
        COMMIT;"""

        for actor in actores:
            script = script_base.format(
                idmovie=movie.id,
                nombreactor=actor.nombre,
                nombrepersonaje=actor.personaje
                )
            operaciones = [{"type":"script","language":"sql","script":[script]}]
            data = {"transaction":True,"operations":operaciones}
            response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
            if (not response.ok):
                break
        return response

    def insertMovieFull (self, movie: Pelicula, director : Director, actores : list):
        '''Inserta una pelicula completa con director y actores/personajes
        '''
        result1 = self.insertMovie(movie=movie)
        result2 = self.insertDirectorMovie(movie=movie,director=director)
        result3 = self.insertActoresPersonajesMovie(movie=movie,actores=actores)
        if (result1.ok and result2.ok and result3.ok):
            return True
        else:
            return False

    def insertSerie (self, serie : Serie):
        '''Inserta una serie
        '''
        script = """
    LET serie = SELECT from Serie where id = '{id}';
    if ($serie.size() = 0) {{
        LET serie = CREATE VERTEX Serie 
        SET titulo = '{tituloserie}',
            id = '{id}',
            imdb_id = '{imdb_id}',
            anio = '{anio}',
            argumento = '{argumento}',
            tagline = '{tagline}',
            urlPoster = '{urlPoster}';
        CREATE EDGE esGenero from $serie to (select from Genero where genero = 'Sci Fi');
    }}"""
        script = script.format(
            id=serie.id,
            tituloserie=serie.titulo.replace("'","`"),
            imdb_id=serie.imdb_id,
            anio=serie.anio,
            argumento=serie.argumento.replace("'","`"),
            tagline=serie.tagline.replace("'","`"),
            urlPoster=serie.urlPoster
            )
        operaciones = [{"type":"script","language":"sql","script":[script]}]
        data = {"transaction":True,"operations":operaciones}
        response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
        return response
    
    def insertActoresPersonajesSerie (self, serie : Serie, actores : list):
        '''Inserta una pelicula
        '''
        script_base = """BEGIN;
        LET serie = SELECT from Serie where id = '{idserie}';
        if ($serie.size() > 0) {{
            LET actor = SELECT from Actor where nombre.toUpperCase() = '{nombreactor}'.toUpperCase();
            if ($actor.size() = 0) {{
                LET actor = CREATE VERTEX Actor SET nombre = '{nombreactor}';
            }}
            LET actuoEn = match
                    {{class:Actor, as: a, where: (nombre.toUpperCase() = '{nombreactor}'.toUpperCase())}}.out('actuoEn') 
                    {{class:Serie, as: p, where: (id = '{idserie}')}} return a;
            if ($actuoEn.size() = 0) {{
                CREATE EDGE actuoEn FROM $actor TO $serie RETRY 100;
            }}
            
            LET personaje = SELECT from Personaje where nombre.toUpperCase() = '{nombrepersonaje}'.toUpperCase();
            if ($personaje.size() = 0) {{
                LET personaje = CREATE VERTEX Personaje SET nombre = '{nombrepersonaje}';
            }}
            LET apareceEn = match
                    {{class:Personaje, as: p, where: (nombre.toUpperCase() = '{nombrepersonaje}'.toUpperCase())}}.out('apareceEn') 
                    {{class:Serie, as: m, where: (id = '{idserie}')}} return a;
            if ($apareceEn.size() = 0) {{
                CREATE EDGE apareceEn FROM $personaje TO $serie RETRY 100;
            }}

            LET interpretoA = match
                    {{class:Actor, as: a, where: (nombre.toUpperCase() = '{nombreactor}'.toUpperCase())}}.out('interpretoA') 
                    {{class:Personaje, as: p, where: (nombre.toUpperCase() = '{nombrepersonaje}'.toUpperCase())}} return a;
            if ($interpretoA.size() = 0) {{
                CREATE EDGE interpretoA FROM $actor TO $personaje RETRY 100;
            }}
        }}
        COMMIT;"""
        response = Response()
        response.status_code = 200
        for actor in actores:
            script = script_base.format(
                idserie=serie.id,
                nombreactor=actor.nombre,
                nombrepersonaje=actor.personaje
                )
            operaciones = [{"type":"script","language":"sql","script":[script]}]
            data = {"transaction":True,"operations":operaciones}
            response = requests.post(self.batchURL,json=data,auth=HTTPBasicAuth(self.user, self.password))
            if (not response.ok):
                break
        return response

    def insertSerieFull (self, serie: Serie, actores : list):
        '''Inserta una serie completa con actores/personajes
        '''
        result1 = self.insertSerie(serie=serie)
        result2 = self.insertActoresPersonajesSerie(serie=serie,actores=actores)
        if (result1.ok and result2.ok):
            return True
        else:
            return False