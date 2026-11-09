try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:  # only needed when DB_ENGINE=mysql
    pass
