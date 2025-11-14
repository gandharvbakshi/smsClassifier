package com.smsclassifier.app.data;

import android.database.Cursor;
import androidx.annotation.NonNull;
import androidx.room.CoroutinesRoom;
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
import java.lang.Float;
import java.lang.Integer;
import java.lang.Long;
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
public final class FeedbackDao_Impl implements FeedbackDao {
  private final RoomDatabase __db;

  private final EntityInsertionAdapter<FeedbackEntity> __insertionAdapterOfFeedbackEntity;

  private final SharedSQLiteStatement __preparedStmtOfDeleteAll;

  public FeedbackDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
    this.__insertionAdapterOfFeedbackEntity = new EntityInsertionAdapter<FeedbackEntity>(__db) {
      @Override
      @NonNull
      protected String createQuery() {
        return "INSERT OR ABORT INTO `feedback` (`id`,`messageId`,`originalIsOtp`,`originalOtpIntent`,`originalIsPhishing`,`originalPhishScore`,`userCorrection`,`timestamp`) VALUES (nullif(?, 0),?,?,?,?,?,?,?)";
      }

      @Override
      protected void bind(@NonNull final SupportSQLiteStatement statement,
          @NonNull final FeedbackEntity entity) {
        statement.bindLong(1, entity.getId());
        statement.bindLong(2, entity.getMessageId());
        final Integer _tmp = entity.getOriginalIsOtp() == null ? null : (entity.getOriginalIsOtp() ? 1 : 0);
        if (_tmp == null) {
          statement.bindNull(3);
        } else {
          statement.bindLong(3, _tmp);
        }
        if (entity.getOriginalOtpIntent() == null) {
          statement.bindNull(4);
        } else {
          statement.bindString(4, entity.getOriginalOtpIntent());
        }
        final Integer _tmp_1 = entity.getOriginalIsPhishing() == null ? null : (entity.getOriginalIsPhishing() ? 1 : 0);
        if (_tmp_1 == null) {
          statement.bindNull(5);
        } else {
          statement.bindLong(5, _tmp_1);
        }
        if (entity.getOriginalPhishScore() == null) {
          statement.bindNull(6);
        } else {
          statement.bindDouble(6, entity.getOriginalPhishScore());
        }
        statement.bindString(7, entity.getUserCorrection());
        statement.bindLong(8, entity.getTimestamp());
      }
    };
    this.__preparedStmtOfDeleteAll = new SharedSQLiteStatement(__db) {
      @Override
      @NonNull
      public String createQuery() {
        final String _query = "DELETE FROM feedback";
        return _query;
      }
    };
  }

  @Override
  public Object insert(final FeedbackEntity feedback,
      final Continuation<? super Long> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Long>() {
      @Override
      @NonNull
      public Long call() throws Exception {
        __db.beginTransaction();
        try {
          final Long _result = __insertionAdapterOfFeedbackEntity.insertAndReturnId(feedback);
          __db.setTransactionSuccessful();
          return _result;
        } finally {
          __db.endTransaction();
        }
      }
    }, $completion);
  }

  @Override
  public Object deleteAll(final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        final SupportSQLiteStatement _stmt = __preparedStmtOfDeleteAll.acquire();
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
          __preparedStmtOfDeleteAll.release(_stmt);
        }
      }
    }, $completion);
  }

  @Override
  public Flow<List<FeedbackEntity>> getAll() {
    final String _sql = "SELECT * FROM feedback ORDER BY timestamp DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"feedback"}, new Callable<List<FeedbackEntity>>() {
      @Override
      @NonNull
      public List<FeedbackEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfMessageId = CursorUtil.getColumnIndexOrThrow(_cursor, "messageId");
          final int _cursorIndexOfOriginalIsOtp = CursorUtil.getColumnIndexOrThrow(_cursor, "originalIsOtp");
          final int _cursorIndexOfOriginalOtpIntent = CursorUtil.getColumnIndexOrThrow(_cursor, "originalOtpIntent");
          final int _cursorIndexOfOriginalIsPhishing = CursorUtil.getColumnIndexOrThrow(_cursor, "originalIsPhishing");
          final int _cursorIndexOfOriginalPhishScore = CursorUtil.getColumnIndexOrThrow(_cursor, "originalPhishScore");
          final int _cursorIndexOfUserCorrection = CursorUtil.getColumnIndexOrThrow(_cursor, "userCorrection");
          final int _cursorIndexOfTimestamp = CursorUtil.getColumnIndexOrThrow(_cursor, "timestamp");
          final List<FeedbackEntity> _result = new ArrayList<FeedbackEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final FeedbackEntity _item;
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final long _tmpMessageId;
            _tmpMessageId = _cursor.getLong(_cursorIndexOfMessageId);
            final Boolean _tmpOriginalIsOtp;
            final Integer _tmp;
            if (_cursor.isNull(_cursorIndexOfOriginalIsOtp)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getInt(_cursorIndexOfOriginalIsOtp);
            }
            _tmpOriginalIsOtp = _tmp == null ? null : _tmp != 0;
            final String _tmpOriginalOtpIntent;
            if (_cursor.isNull(_cursorIndexOfOriginalOtpIntent)) {
              _tmpOriginalOtpIntent = null;
            } else {
              _tmpOriginalOtpIntent = _cursor.getString(_cursorIndexOfOriginalOtpIntent);
            }
            final Boolean _tmpOriginalIsPhishing;
            final Integer _tmp_1;
            if (_cursor.isNull(_cursorIndexOfOriginalIsPhishing)) {
              _tmp_1 = null;
            } else {
              _tmp_1 = _cursor.getInt(_cursorIndexOfOriginalIsPhishing);
            }
            _tmpOriginalIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
            final Float _tmpOriginalPhishScore;
            if (_cursor.isNull(_cursorIndexOfOriginalPhishScore)) {
              _tmpOriginalPhishScore = null;
            } else {
              _tmpOriginalPhishScore = _cursor.getFloat(_cursorIndexOfOriginalPhishScore);
            }
            final String _tmpUserCorrection;
            _tmpUserCorrection = _cursor.getString(_cursorIndexOfUserCorrection);
            final long _tmpTimestamp;
            _tmpTimestamp = _cursor.getLong(_cursorIndexOfTimestamp);
            _item = new FeedbackEntity(_tmpId,_tmpMessageId,_tmpOriginalIsOtp,_tmpOriginalOtpIntent,_tmpOriginalIsPhishing,_tmpOriginalPhishScore,_tmpUserCorrection,_tmpTimestamp);
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
