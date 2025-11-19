package com.smsclassifier.app.data;

import androidx.annotation.NonNull;
import androidx.room.DatabaseConfiguration;
import androidx.room.InvalidationTracker;
import androidx.room.RoomDatabase;
import androidx.room.RoomOpenHelper;
import androidx.room.migration.AutoMigrationSpec;
import androidx.room.migration.Migration;
import androidx.room.util.DBUtil;
import androidx.room.util.TableInfo;
import androidx.sqlite.db.SupportSQLiteDatabase;
import androidx.sqlite.db.SupportSQLiteOpenHelper;
import java.lang.Class;
import java.lang.Override;
import java.lang.String;
import java.lang.SuppressWarnings;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.annotation.processing.Generated;

@Generated("androidx.room.RoomProcessor")
@SuppressWarnings({"unchecked", "deprecation"})
public final class AppDatabase_Impl extends AppDatabase {
  private volatile MessageDao _messageDao;

  private volatile FeedbackDao _feedbackDao;

  private volatile MisclassificationLogDao _misclassificationLogDao;

  @Override
  @NonNull
  protected SupportSQLiteOpenHelper createOpenHelper(@NonNull final DatabaseConfiguration config) {
    final SupportSQLiteOpenHelper.Callback _openCallback = new RoomOpenHelper(config, new RoomOpenHelper.Delegate(2) {
      @Override
      public void createAllTables(@NonNull final SupportSQLiteDatabase db) {
        db.execSQL("CREATE TABLE IF NOT EXISTS `messages` (`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `sender` TEXT NOT NULL, `body` TEXT NOT NULL, `ts` INTEGER NOT NULL, `language` TEXT, `featuresJson` TEXT, `isOtp` INTEGER, `otpIntent` TEXT, `isPhishing` INTEGER, `phishScore` REAL, `reasonsJson` TEXT, `reviewed` INTEGER NOT NULL, `version` INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE IF NOT EXISTS `feedback` (`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `messageId` INTEGER NOT NULL, `originalIsOtp` INTEGER, `originalOtpIntent` TEXT, `originalIsPhishing` INTEGER, `originalPhishScore` REAL, `userCorrection` TEXT NOT NULL, `timestamp` INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE IF NOT EXISTS `misclassification_logs` (`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `messageId` INTEGER NOT NULL, `sender` TEXT NOT NULL, `body` TEXT NOT NULL, `predictedIsOtp` INTEGER, `predictedOtpIntent` TEXT, `predictedIsPhishing` INTEGER, `createdAt` INTEGER NOT NULL, `userNote` TEXT)");
        db.execSQL("CREATE TABLE IF NOT EXISTS room_master_table (id INTEGER PRIMARY KEY,identity_hash TEXT)");
        db.execSQL("INSERT OR REPLACE INTO room_master_table (id,identity_hash) VALUES(42, '7e5998bf9cb10a9c9020c47dcfc19105')");
      }

      @Override
      public void dropAllTables(@NonNull final SupportSQLiteDatabase db) {
        db.execSQL("DROP TABLE IF EXISTS `messages`");
        db.execSQL("DROP TABLE IF EXISTS `feedback`");
        db.execSQL("DROP TABLE IF EXISTS `misclassification_logs`");
        final List<? extends RoomDatabase.Callback> _callbacks = mCallbacks;
        if (_callbacks != null) {
          for (RoomDatabase.Callback _callback : _callbacks) {
            _callback.onDestructiveMigration(db);
          }
        }
      }

      @Override
      public void onCreate(@NonNull final SupportSQLiteDatabase db) {
        final List<? extends RoomDatabase.Callback> _callbacks = mCallbacks;
        if (_callbacks != null) {
          for (RoomDatabase.Callback _callback : _callbacks) {
            _callback.onCreate(db);
          }
        }
      }

      @Override
      public void onOpen(@NonNull final SupportSQLiteDatabase db) {
        mDatabase = db;
        internalInitInvalidationTracker(db);
        final List<? extends RoomDatabase.Callback> _callbacks = mCallbacks;
        if (_callbacks != null) {
          for (RoomDatabase.Callback _callback : _callbacks) {
            _callback.onOpen(db);
          }
        }
      }

      @Override
      public void onPreMigrate(@NonNull final SupportSQLiteDatabase db) {
        DBUtil.dropFtsSyncTriggers(db);
      }

      @Override
      public void onPostMigrate(@NonNull final SupportSQLiteDatabase db) {
      }

      @Override
      @NonNull
      public RoomOpenHelper.ValidationResult onValidateSchema(
          @NonNull final SupportSQLiteDatabase db) {
        final HashMap<String, TableInfo.Column> _columnsMessages = new HashMap<String, TableInfo.Column>(13);
        _columnsMessages.put("id", new TableInfo.Column("id", "INTEGER", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("sender", new TableInfo.Column("sender", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("body", new TableInfo.Column("body", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("ts", new TableInfo.Column("ts", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("language", new TableInfo.Column("language", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("featuresJson", new TableInfo.Column("featuresJson", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("isOtp", new TableInfo.Column("isOtp", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("otpIntent", new TableInfo.Column("otpIntent", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("isPhishing", new TableInfo.Column("isPhishing", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("phishScore", new TableInfo.Column("phishScore", "REAL", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("reasonsJson", new TableInfo.Column("reasonsJson", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("reviewed", new TableInfo.Column("reviewed", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMessages.put("version", new TableInfo.Column("version", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysMessages = new HashSet<TableInfo.ForeignKey>(0);
        final HashSet<TableInfo.Index> _indicesMessages = new HashSet<TableInfo.Index>(0);
        final TableInfo _infoMessages = new TableInfo("messages", _columnsMessages, _foreignKeysMessages, _indicesMessages);
        final TableInfo _existingMessages = TableInfo.read(db, "messages");
        if (!_infoMessages.equals(_existingMessages)) {
          return new RoomOpenHelper.ValidationResult(false, "messages(com.smsclassifier.app.data.MessageEntity).\n"
                  + " Expected:\n" + _infoMessages + "\n"
                  + " Found:\n" + _existingMessages);
        }
        final HashMap<String, TableInfo.Column> _columnsFeedback = new HashMap<String, TableInfo.Column>(8);
        _columnsFeedback.put("id", new TableInfo.Column("id", "INTEGER", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsFeedback.put("messageId", new TableInfo.Column("messageId", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsFeedback.put("originalIsOtp", new TableInfo.Column("originalIsOtp", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsFeedback.put("originalOtpIntent", new TableInfo.Column("originalOtpIntent", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsFeedback.put("originalIsPhishing", new TableInfo.Column("originalIsPhishing", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsFeedback.put("originalPhishScore", new TableInfo.Column("originalPhishScore", "REAL", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsFeedback.put("userCorrection", new TableInfo.Column("userCorrection", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsFeedback.put("timestamp", new TableInfo.Column("timestamp", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysFeedback = new HashSet<TableInfo.ForeignKey>(0);
        final HashSet<TableInfo.Index> _indicesFeedback = new HashSet<TableInfo.Index>(0);
        final TableInfo _infoFeedback = new TableInfo("feedback", _columnsFeedback, _foreignKeysFeedback, _indicesFeedback);
        final TableInfo _existingFeedback = TableInfo.read(db, "feedback");
        if (!_infoFeedback.equals(_existingFeedback)) {
          return new RoomOpenHelper.ValidationResult(false, "feedback(com.smsclassifier.app.data.FeedbackEntity).\n"
                  + " Expected:\n" + _infoFeedback + "\n"
                  + " Found:\n" + _existingFeedback);
        }
        final HashMap<String, TableInfo.Column> _columnsMisclassificationLogs = new HashMap<String, TableInfo.Column>(9);
        _columnsMisclassificationLogs.put("id", new TableInfo.Column("id", "INTEGER", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMisclassificationLogs.put("messageId", new TableInfo.Column("messageId", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMisclassificationLogs.put("sender", new TableInfo.Column("sender", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMisclassificationLogs.put("body", new TableInfo.Column("body", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMisclassificationLogs.put("predictedIsOtp", new TableInfo.Column("predictedIsOtp", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMisclassificationLogs.put("predictedOtpIntent", new TableInfo.Column("predictedOtpIntent", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMisclassificationLogs.put("predictedIsPhishing", new TableInfo.Column("predictedIsPhishing", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMisclassificationLogs.put("createdAt", new TableInfo.Column("createdAt", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsMisclassificationLogs.put("userNote", new TableInfo.Column("userNote", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysMisclassificationLogs = new HashSet<TableInfo.ForeignKey>(0);
        final HashSet<TableInfo.Index> _indicesMisclassificationLogs = new HashSet<TableInfo.Index>(0);
        final TableInfo _infoMisclassificationLogs = new TableInfo("misclassification_logs", _columnsMisclassificationLogs, _foreignKeysMisclassificationLogs, _indicesMisclassificationLogs);
        final TableInfo _existingMisclassificationLogs = TableInfo.read(db, "misclassification_logs");
        if (!_infoMisclassificationLogs.equals(_existingMisclassificationLogs)) {
          return new RoomOpenHelper.ValidationResult(false, "misclassification_logs(com.smsclassifier.app.data.MisclassificationLogEntity).\n"
                  + " Expected:\n" + _infoMisclassificationLogs + "\n"
                  + " Found:\n" + _existingMisclassificationLogs);
        }
        return new RoomOpenHelper.ValidationResult(true, null);
      }
    }, "7e5998bf9cb10a9c9020c47dcfc19105", "e3a4b3f3b4bb59b5c7e222606edf99b5");
    final SupportSQLiteOpenHelper.Configuration _sqliteConfig = SupportSQLiteOpenHelper.Configuration.builder(config.context).name(config.name).callback(_openCallback).build();
    final SupportSQLiteOpenHelper _helper = config.sqliteOpenHelperFactory.create(_sqliteConfig);
    return _helper;
  }

  @Override
  @NonNull
  protected InvalidationTracker createInvalidationTracker() {
    final HashMap<String, String> _shadowTablesMap = new HashMap<String, String>(0);
    final HashMap<String, Set<String>> _viewTables = new HashMap<String, Set<String>>(0);
    return new InvalidationTracker(this, _shadowTablesMap, _viewTables, "messages","feedback","misclassification_logs");
  }

  @Override
  public void clearAllTables() {
    super.assertNotMainThread();
    final SupportSQLiteDatabase _db = super.getOpenHelper().getWritableDatabase();
    try {
      super.beginTransaction();
      _db.execSQL("DELETE FROM `messages`");
      _db.execSQL("DELETE FROM `feedback`");
      _db.execSQL("DELETE FROM `misclassification_logs`");
      super.setTransactionSuccessful();
    } finally {
      super.endTransaction();
      _db.query("PRAGMA wal_checkpoint(FULL)").close();
      if (!_db.inTransaction()) {
        _db.execSQL("VACUUM");
      }
    }
  }

  @Override
  @NonNull
  protected Map<Class<?>, List<Class<?>>> getRequiredTypeConverters() {
    final HashMap<Class<?>, List<Class<?>>> _typeConvertersMap = new HashMap<Class<?>, List<Class<?>>>();
    _typeConvertersMap.put(MessageDao.class, MessageDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(FeedbackDao.class, FeedbackDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(MisclassificationLogDao.class, MisclassificationLogDao_Impl.getRequiredConverters());
    return _typeConvertersMap;
  }

  @Override
  @NonNull
  public Set<Class<? extends AutoMigrationSpec>> getRequiredAutoMigrationSpecs() {
    final HashSet<Class<? extends AutoMigrationSpec>> _autoMigrationSpecsSet = new HashSet<Class<? extends AutoMigrationSpec>>();
    return _autoMigrationSpecsSet;
  }

  @Override
  @NonNull
  public List<Migration> getAutoMigrations(
      @NonNull final Map<Class<? extends AutoMigrationSpec>, AutoMigrationSpec> autoMigrationSpecs) {
    final List<Migration> _autoMigrations = new ArrayList<Migration>();
    return _autoMigrations;
  }

  @Override
  public MessageDao messageDao() {
    if (_messageDao != null) {
      return _messageDao;
    } else {
      synchronized(this) {
        if(_messageDao == null) {
          _messageDao = new MessageDao_Impl(this);
        }
        return _messageDao;
      }
    }
  }

  @Override
  public FeedbackDao feedbackDao() {
    if (_feedbackDao != null) {
      return _feedbackDao;
    } else {
      synchronized(this) {
        if(_feedbackDao == null) {
          _feedbackDao = new FeedbackDao_Impl(this);
        }
        return _feedbackDao;
      }
    }
  }

  @Override
  public MisclassificationLogDao misclassificationLogDao() {
    if (_misclassificationLogDao != null) {
      return _misclassificationLogDao;
    } else {
      synchronized(this) {
        if(_misclassificationLogDao == null) {
          _misclassificationLogDao = new MisclassificationLogDao_Impl(this);
        }
        return _misclassificationLogDao;
      }
    }
  }
}
