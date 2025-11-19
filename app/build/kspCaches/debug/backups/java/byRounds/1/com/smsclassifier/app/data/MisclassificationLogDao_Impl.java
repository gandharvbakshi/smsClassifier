package com.smsclassifier.app.data;

import android.database.Cursor;
import androidx.annotation.NonNull;
import androidx.room.CoroutinesRoom;
import androidx.room.EntityDeletionOrUpdateAdapter;
import androidx.room.EntityInsertionAdapter;
import androidx.room.RoomDatabase;
import androidx.room.RoomSQLiteQuery;
import androidx.room.SharedSQLiteStatement;
import androidx.room.util.CursorUtil;
import androidx.room.util.DBUtil;
import androidx.sqlite.db.SupportSQLiteStatement;
import java.lang.Boolean;
import java.lang.Class;
import java.lang.Exception;
import java.lang.Integer;
import java.lang.Object;
import java.lang.Override;
import java.lang.String;
import java.lang.SuppressWarnings;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Callable;
import javax.annotation.processing.Generated;
import kotlin.Unit;
import kotlin.coroutines.Continuation;
import kotlinx.coroutines.flow.Flow;

@Generated("androidx.room.RoomProcessor")
@SuppressWarnings({"unchecked", "deprecation"})
public final class MisclassificationLogDao_Impl implements MisclassificationLogDao {
  private final RoomDatabase __db;

  private final EntityInsertionAdapter<MisclassificationLogEntity> __insertionAdapterOfMisclassificationLogEntity;

  private final EntityDeletionOrUpdateAdapter<MisclassificationLogEntity> __deletionAdapterOfMisclassificationLogEntity;

  private final SharedSQLiteStatement __preparedStmtOfClear;

  public MisclassificationLogDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
    this.__insertionAdapterOfMisclassificationLogEntity = new EntityInsertionAdapter<MisclassificationLogEntity>(__db) {
      @Override
      @NonNull
      protected String createQuery() {
        return "INSERT OR ABORT INTO `misclassification_logs` (`id`,`messageId`,`sender`,`body`,`predictedIsOtp`,`predictedOtpIntent`,`predictedIsPhishing`,`createdAt`,`userNote`) VALUES (nullif(?, 0),?,?,?,?,?,?,?,?)";
      }

      @Override
      protected void bind(@NonNull final SupportSQLiteStatement statement,
          @NonNull final MisclassificationLogEntity entity) {
        statement.bindLong(1, entity.getId());
        statement.bindLong(2, entity.getMessageId());
        statement.bindString(3, entity.getSender());
        statement.bindString(4, entity.getBody());
        final Integer _tmp = entity.getPredictedIsOtp() == null ? null : (entity.getPredictedIsOtp() ? 1 : 0);
        if (_tmp == null) {
          statement.bindNull(5);
        } else {
          statement.bindLong(5, _tmp);
        }
        if (entity.getPredictedOtpIntent() == null) {
          statement.bindNull(6);
        } else {
          statement.bindString(6, entity.getPredictedOtpIntent());
        }
        final Integer _tmp_1 = entity.getPredictedIsPhishing() == null ? null : (entity.getPredictedIsPhishing() ? 1 : 0);
        if (_tmp_1 == null) {
          statement.bindNull(7);
        } else {
          statement.bindLong(7, _tmp_1);
        }
        statement.bindLong(8, entity.getCreatedAt());
        if (entity.getUserNote() == null) {
          statement.bindNull(9);
        } else {
          statement.bindString(9, entity.getUserNote());
        }
      }
    };
    this.__deletionAdapterOfMisclassificationLogEntity = new EntityDeletionOrUpdateAdapter<MisclassificationLogEntity>(__db) {
      @Override
      @NonNull
      protected String createQuery() {
        return "DELETE FROM `misclassification_logs` WHERE `id` = ?";
      }

      @Override
      protected void bind(@NonNull final SupportSQLiteStatement statement,
          @NonNull final MisclassificationLogEntity entity) {
        statement.bindLong(1, entity.getId());
      }
    };
    this.__preparedStmtOfClear = new SharedSQLiteStatement(__db) {
      @Override
      @NonNull
      public String createQuery() {
        final String _query = "DELETE FROM misclassification_logs";
        return _query;
      }
    };
  }

  @Override
  public Object insert(final MisclassificationLogEntity log,
      final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        __db.beginTransaction();
        try {
          __insertionAdapterOfMisclassificationLogEntity.insert(log);
          __db.setTransactionSuccessful();
          return Unit.INSTANCE;
        } finally {
          __db.endTransaction();
        }
      }
    }, $completion);
  }

  @Override
  public Object delete(final MisclassificationLogEntity log,
      final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        __db.beginTransaction();
        try {
          __deletionAdapterOfMisclassificationLogEntity.handle(log);
          __db.setTransactionSuccessful();
          return Unit.INSTANCE;
        } finally {
          __db.endTransaction();
        }
      }
    }, $completion);
  }

  @Override
  public Object clear(final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        final SupportSQLiteStatement _stmt = __preparedStmtOfClear.acquire();
        try {
          __db.beginTransaction();
          try {
            _stmt.executeUpdateDelete();
            __db.setTransactionSuccessful();
            return Unit.INSTANCE;
          } finally {
            __db.endTransaction();
          }
        } finally {
          __preparedStmtOfClear.release(_stmt);
        }
      }
    }, $completion);
  }

  @Override
  public Flow<List<MisclassificationLogEntity>> getAll() {
    final String _sql = "SELECT * FROM misclassification_logs ORDER BY createdAt DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"misclassification_logs"}, new Callable<List<MisclassificationLogEntity>>() {
      @Override
      @NonNull
      public List<MisclassificationLogEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfMessageId = CursorUtil.getColumnIndexOrThrow(_cursor, "messageId");
          final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(_cursor, "sender");
          final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(_cursor, "body");
          final int _cursorIndexOfPredictedIsOtp = CursorUtil.getColumnIndexOrThrow(_cursor, "predictedIsOtp");
          final int _cursorIndexOfPredictedOtpIntent = CursorUtil.getColumnIndexOrThrow(_cursor, "predictedOtpIntent");
          final int _cursorIndexOfPredictedIsPhishing = CursorUtil.getColumnIndexOrThrow(_cursor, "predictedIsPhishing");
          final int _cursorIndexOfCreatedAt = CursorUtil.getColumnIndexOrThrow(_cursor, "createdAt");
          final int _cursorIndexOfUserNote = CursorUtil.getColumnIndexOrThrow(_cursor, "userNote");
          final List<MisclassificationLogEntity> _result = new ArrayList<MisclassificationLogEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final MisclassificationLogEntity _item;
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final long _tmpMessageId;
            _tmpMessageId = _cursor.getLong(_cursorIndexOfMessageId);
            final String _tmpSender;
            _tmpSender = _cursor.getString(_cursorIndexOfSender);
            final String _tmpBody;
            _tmpBody = _cursor.getString(_cursorIndexOfBody);
            final Boolean _tmpPredictedIsOtp;
            final Integer _tmp;
            if (_cursor.isNull(_cursorIndexOfPredictedIsOtp)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getInt(_cursorIndexOfPredictedIsOtp);
            }
            _tmpPredictedIsOtp = _tmp == null ? null : _tmp != 0;
            final String _tmpPredictedOtpIntent;
            if (_cursor.isNull(_cursorIndexOfPredictedOtpIntent)) {
              _tmpPredictedOtpIntent = null;
            } else {
              _tmpPredictedOtpIntent = _cursor.getString(_cursorIndexOfPredictedOtpIntent);
            }
            final Boolean _tmpPredictedIsPhishing;
            final Integer _tmp_1;
            if (_cursor.isNull(_cursorIndexOfPredictedIsPhishing)) {
              _tmp_1 = null;
            } else {
              _tmp_1 = _cursor.getInt(_cursorIndexOfPredictedIsPhishing);
            }
            _tmpPredictedIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
            final long _tmpCreatedAt;
            _tmpCreatedAt = _cursor.getLong(_cursorIndexOfCreatedAt);
            final String _tmpUserNote;
            if (_cursor.isNull(_cursorIndexOfUserNote)) {
              _tmpUserNote = null;
            } else {
              _tmpUserNote = _cursor.getString(_cursorIndexOfUserNote);
            }
            _item = new MisclassificationLogEntity(_tmpId,_tmpMessageId,_tmpSender,_tmpBody,_tmpPredictedIsOtp,_tmpPredictedOtpIntent,_tmpPredictedIsPhishing,_tmpCreatedAt,_tmpUserNote);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @NonNull
  public static List<Class<?>> getRequiredConverters() {
    return Collections.emptyList();
  }
}
